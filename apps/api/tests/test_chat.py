"""Alden's tool loop, with a scripted fake LLM."""

import json
from types import SimpleNamespace as NS

import pytest


def _chunk(content=None, tool_calls=None):
    return NS(choices=[NS(delta=NS(content=content, tool_calls=tool_calls))])


def _tool_call(name, args, call_id):
    return _chunk(tool_calls=[NS(index=0, id=call_id, function=NS(name=name, arguments=json.dumps(args)))])


class ScriptedLLM:
    """Round 1: search foods. Round 2: propose logging the first result. Round 3: answer citing it."""

    def __init__(self):
        self.calls = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if not tool_results:
            return iter([_tool_call("search_foods", {"query": "egg"}, "c1")])
        if len(tool_results) == 1:
            food = json.loads(tool_results[0]["content"])["results"][0]
            self.food = food
            return iter([_tool_call("propose_meal_log", {"meal": "breakfast", "items": [{"food_id": food["food_id"], "grams": 100}]}, "c2")])
        return iter([_chunk("Two eggs have about "), _chunk(f"12.6 g of protein [{self.food['cite_as']}].")])


def _events(text):
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


@pytest.fixture
def llm(monkeypatch):
    fake = ScriptedLLM()
    import betteru.llm.agent as agent

    monkeypatch.setattr(agent, "get_llm", lambda: fake)
    return fake


def test_tool_loop_streams_answer_sources_and_actions(user_client, foods, llm):
    r = user_client.post("/api/chat", json={"message": "I had two eggs"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = _events(r.text)
    kinds = [e for e, _ in events]
    assert "status" in kinds and kinds[-1] == "done"
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert answer.endswith("[F1].")
    sources = next(d["sources"] for e, d in events if e == "sources")
    assert sources == [{"id": "F1", "title": "Egg, whole, raw, fresh",
                        "url": "https://fdc.nal.usda.gov/food-details/1/nutrients", "kind": "food"}]
    action = next(d["actions"] for e, d in events if e == "actions")[0]
    assert action["type"] == "log_meal" and action["payload"]["items"][0]["kcal"] == 143

    # The system prompt carries the profile, and nothing was logged without confirmation.
    system = llm.calls[0]["messages"][0]["content"]
    assert "allergies: peanut" in system and "vegetarian" in system
    assert user_client.get("/api/log/" + __import__("datetime").date.today().isoformat()).json()["entries"] == []

    history = user_client.get("/api/chat/messages").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["sources"][0]["id"] == "F1"


def test_allergy_warning_in_food_results(user_client, foods, db):
    from betteru.llm.tools import ToolContext, t_search_foods
    from betteru.models import User

    ctx = ToolContext(db=db, user=db.query(User).one())
    results = t_search_foods(ctx, "peanut butter")["results"]
    flagged = [r for r in results if r["name"].startswith("Peanut")]
    assert flagged and "allergic" in flagged[0]["allergy_warning"]


def test_daily_limit(user_client, monkeypatch, llm):
    from betteru.config import get_settings

    monkeypatch.setattr(get_settings(), "llm_daily_message_limit", 0)
    assert user_client.post("/api/chat", json={"message": "hi"}).status_code == 429


def test_llm_failure_reports_error(user_client, monkeypatch):
    import betteru.llm.agent as agent

    def boom(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(agent, "get_llm", lambda: NS(chat=NS(completions=NS(create=boom))))
    events = _events(user_client.post("/api/chat", json={"message": "hi"}).text)
    assert events[-1][0] == "error"


def test_log_button_backstop(user_client, foods, monkeypatch):
    """If the model calculates a meal the user ate but forgets propose_meal_log, the server adds the button."""
    import betteru.llm.agent as agent

    class ForgetsToLog:
        def __init__(self):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kwargs):
            if not any(m.get("role") == "tool" for m in kwargs["messages"]):
                return iter([_tool_call("calculate_meal", {"items": [{"food_id": foods["egg"], "grams": 50}]}, "c1")])
            return iter([_chunk("That's about 6 g of protein.")])

    monkeypatch.setattr(agent, "get_llm", lambda: ForgetsToLog())
    events = _events(user_client.post("/api/chat", json={"message": "I had an egg for breakfast"}).text)
    action = next(d["actions"] for e, d in events if e == "actions")[0]
    assert action["type"] == "log_meal" and action["payload"]["meal"] == "breakfast"


def test_no_backstop_for_questions(user_client, foods, monkeypatch):
    import betteru.llm.agent as agent

    class Calculates:
        def __init__(self):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kwargs):
            if not any(m.get("role") == "tool" for m in kwargs["messages"]):
                return iter([_tool_call("calculate_meal", {"items": [{"food_id": foods["egg"], "grams": 50}]}, "c1")])
            return iter([_chunk("About 6 g.")])

    monkeypatch.setattr(agent, "get_llm", lambda: Calculates())
    events = _events(user_client.post("/api/chat", json={"message": "How much protein is in an egg?"}).text)
    assert "actions" not in [e for e, _ in events]


def test_consume_action(user_client, foods, llm):
    user_client.post("/api/chat", json={"message": "I had two eggs"})
    msg = user_client.get("/api/chat/messages").json()[-1]
    assert len(msg["actions"]) == 1
    assert user_client.delete(f"/api/chat/messages/{msg['id']}/actions/0").status_code == 204
    assert user_client.get("/api/chat/messages").json()[-1]["actions"] == []
    assert user_client.delete(f"/api/chat/messages/{msg['id']}/actions/0").status_code == 404


def test_retries_malformed_tool_call(user_client, foods, monkeypatch):
    """Groq can reject a malformed tool call mid-stream; the round is retried."""
    import betteru.llm.agent as agent

    class Flaky:
        def __init__(self):
            self.calls = 0
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                def broken():
                    raise RuntimeError("Failed to parse tool call arguments as JSON")
                    yield  # pragma: no cover
                return broken()
            return iter([_chunk("All good.")])

    flaky = Flaky()
    monkeypatch.setattr(agent, "get_llm", lambda: flaky)
    events = _events(user_client.post("/api/chat", json={"message": "hi"}).text)
    assert events[-1][0] == "done" and flaky.calls == 2
    assert "".join(d["text"] for e, d in events if e == "token") == "All good."
