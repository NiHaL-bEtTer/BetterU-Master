"""Alden's tool-calling loop, streamed as typed events.

Events (sent to the browser as Server-Sent Events):
  status   {"text"}                      — "Looking up foods…"
  token    {"text"}                      — a piece of the answer
  sources  {"sources": [...]}            — citations used in the answer
  actions  {"actions": [...]}            — confirmation buttons (log meal, build plan)
  video    {"video_id"}                  — recipe video to embed
  done     {"message_id"}
  error    {"message"}
"""

import json
import logging
import re
import time
from collections.abc import Iterator
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from betteru.clients.llm import get_llm, model_options
from betteru.config import get_settings
from betteru.llm.prompts import system_prompt
from betteru.llm.tools import STATUS_TEXT, ToolContext, run_tool, t_propose_meal_log, tool_specs
from betteru.models import ChatMessage, User
from betteru.services import food_log
from betteru.services.targets import targets_for

log = logging.getLogger(__name__)

MAX_ROUNDS = 6
_CITE_RE = re.compile(r"[【\[]\s*([FSW]\d+)\s*[】\]]")


_ATE_RE = re.compile(r"\b(i\s+(just\s+)?(ate|had|drank|eaten)|i've\s+(eaten|had)|for (breakfast|lunch|dinner)|log\b)", re.I)
_MEAL_WORDS = ("breakfast", "lunch", "dinner", "snack")


def guess_meal(message: str, hour: int) -> str:
    lowered = message.lower()
    for meal in _MEAL_WORDS:
        if meal in lowered:
            return meal
    return "breakfast" if hour < 11 else "lunch" if hour < 15 else "dinner" if hour < 21 else "snack"


def normalize_citations(text: str) -> str:
    return _CITE_RE.sub(lambda m: f"[{m.group(1)}]", text)
HISTORY_TURNS = 10


def _history(db: Session, user: User) -> list[dict]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(HISTORY_TURNS)
    ).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def run_chat(db: Session, user: User, message: str) -> Iterator[tuple[str, dict]]:
    settings = get_settings()
    history = _history(db, user)

    db.add(ChatMessage(user_id=user.id, role="user", content=message, sources=[], actions=[]))
    db.commit()

    today = food_log.totals(food_log.entries_for_day(db, user, date.today()))
    messages: list[dict] = [
        {"role": "system", "content": system_prompt(user.profile, targets_for(user.profile), today)},
        *history,
        {"role": "user", "content": message},
    ]
    ctx = ToolContext(db=db, user=user)
    tools = tool_specs(web_enabled=bool(settings.tavily_api_key), video_enabled=bool(settings.youtube_api_key))
    answer = ""

    retries = 0
    try:
        for round_no in range(MAX_ROUNDS):
            # On the last round, force a plain answer so the loop always ends.
            final_round = round_no == MAX_ROUNDS - 1
            started = time.perf_counter()
            stream = get_llm().chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                tools=tools,
                tool_choice="none" if final_round else "auto",
                parallel_tool_calls=True,
                temperature=0.3,
                max_tokens=2500,  # reasoning models count their thinking here too
                stream=True,
                **model_options(),
            )
            text_parts: list[str] = []
            calls: dict[int, dict] = {}
            try:
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        text_parts.append(delta.content)
                        yield "token", {"text": delta.content}
                    for tc in delta.tool_calls or []:
                        slot = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                        if tc.id:
                            slot["id"] = tc.id
                        if tc.function and tc.function.name:
                            slot["name"] += tc.function.name
                        if tc.function and tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
            except Exception as e:  # noqa: BLE001
                # Providers that validate tool calls server-side (e.g. Groq) reject a malformed
                # call mid-stream. Sampling again almost always produces a valid one.
                if "tool call" in str(e).lower() and retries < 2 and not text_parts:
                    retries += 1
                    log.warning("Retrying round %d after invalid tool call: %s", round_no, e)
                    continue
                raise

            answer += "".join(text_parts)
            log.info("chat round %d: %.1fs, tools=%s", round_no, time.perf_counter() - started,
                     [c["name"] for c in calls.values()])
            if not calls:
                break

            ordered = [calls[i] for i in sorted(calls)]
            messages.append({
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {"id": c["id"] or f"call_{round_no}_{i}", "type": "function",
                     "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                    for i, c in enumerate(ordered)
                ],
            })
            for i, c in enumerate(ordered):
                yield "status", {"text": STATUS_TEXT.get(c["name"], "Working…")}
                result = run_tool(ctx, c["name"], c["arguments"])
                messages.append({"role": "tool", "tool_call_id": c["id"] or f"call_{round_no}_{i}", "content": result})
    except Exception as e:  # noqa: BLE001
        log.exception("Chat failed")
        msg = "Sorry — I couldn't finish that answer. Please try again in a moment."
        if "rate" in str(e).lower():
            msg = "I'm getting a lot of requests right now. Please try again in a minute."
        yield "error", {"message": msg}
        if not answer:
            return

    # Backstop: the user said they ate something and Alden worked out the meal, but the model
    # forgot to offer the log button. Offer it deterministically (the user still confirms).
    if (ctx.last_meal_items and _ATE_RE.search(message)
            and not any(a["type"] == "log_meal" for a in ctx.actions)):
        from datetime import datetime
        t_propose_meal_log(ctx, guess_meal(message, datetime.now().hour), ctx.last_meal_items)

    # Some models write citations with full-width brackets (【F12】); normalise them.
    answer = normalize_citations(answer)
    # Only return citations the answer actually uses.
    used = [s for sid, s in ctx.sources.items() if f"[{sid}]" in answer]
    if not used:
        # The model didn't cite inline: still show where the numbers came from.
        used = [ctx.sources[sid] for sid in dict.fromkeys(ctx.relied_on) if sid in ctx.sources]
    if used:
        yield "sources", {"sources": used}
    if ctx.actions:
        yield "actions", {"actions": ctx.actions}
    if ctx.video_id:
        yield "video", {"video_id": ctx.video_id}

    reply = ChatMessage(
        user_id=user.id, role="assistant", content=answer.strip(),
        sources=used, actions=ctx.actions, video_id=ctx.video_id,
    )
    db.add(reply)
    db.commit()
    yield "done", {"message_id": reply.id}


def to_sse(events: Iterator[tuple[str, dict]]) -> Iterator[str]:
    for event, data in events:
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
