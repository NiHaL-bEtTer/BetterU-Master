"""Workout plan generation from the local exercise table (free-exercise-db).

The LLM only chooses and arranges exercises from a candidate list we give it;
every exercise id it returns is validated against the database.
"""

import json
import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from betteru.clients.llm import complete
from betteru.models import Exercise, User, WorkoutPlan, WorkoutSet
from betteru.schemas import ExerciseOut, PlanDay, PlanExercise, WorkoutPlanOut

log = logging.getLogger(__name__)

MUSCLES = [
    "chest", "lats", "middle back", "lower back", "shoulders", "biceps", "triceps",
    "quadriceps", "hamstrings", "glutes", "calves", "abdominals", "traps", "forearms",
]
LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "expert": 2}

PLAN_SYSTEM = """You are Alden, BetterU's strength coach. Build a weekly workout plan using ONLY exercises from the candidate list (refer to them by their numeric id).

Return JSON only, in this shape:
{"title": str, "description": str (one sentence),
 "days": [{"day": "Day 1", "focus": "Upper body",
           "exercises": [{"exercise_id": int, "sets": int, "reps": "8-12", "rest_sec": int, "note": str}]}]}

Rules:
- Exactly the requested number of training days; 4-6 exercises per day.
- Balance push/pull/legs across the week; start each day with the hardest compound lift.
- Goal "cut": moderate reps (10-15), shorter rest. Goal "bulk": 6-12 reps, longer rest on compounds. Beginners: 2-3 sets.
- Notes are one short form cue.
- Honor anything the user asked for (focus areas, time limits, injuries: avoid exercises that load an injured area)."""


def _candidates(db: Session, equipment: list[str], level_cap: int) -> list[Exercise]:
    allowed = set(equipment or []) | {"body only"}
    rows = db.scalars(
        select(Exercise).where(Exercise.category.in_(["strength", "powerlifting", "plyometrics", "cardio"]))
    ).all()
    by_muscle: dict[str, list[Exercise]] = {m: [] for m in MUSCLES}
    for ex in rows:
        if ex.equipment not in allowed and ex.equipment != "other":
            continue
        if LEVEL_ORDER.get(ex.level, 1) > level_cap:
            continue
        for m in ex.primary_muscles[:1]:
            if m in by_muscle:
                by_muscle[m].append(ex)
    picked: list[Exercise] = []
    for m in MUSCLES:
        # Prefer simpler, well-known lifts: easier levels first, shorter names as a tiebreak.
        options = sorted(by_muscle[m], key=lambda e: (LEVEL_ORDER.get(e.level, 1), len(e.name)))
        picked.extend(options[:7])
    return picked


def generate_plan(db: Session, user: User, request: str) -> WorkoutPlan:
    p = user.profile
    equipment = p.equipment if p else []
    days = p.training_days if p else 3
    level_cap = 1  # beginner + intermediate; experts can ask in the request
    if "advanced" in request.lower() or "expert" in request.lower():
        level_cap = 2

    candidates = _candidates(db, equipment, level_cap)
    if not candidates:
        raise ValueError("No exercises available — run the exercise ingestion first.")
    by_id = {e.id: e for e in candidates}

    profile_line = (
        f"Goal: {p.goal}; age {p.age}; sex {p.sex}; training days per week: {days}; "
        f"equipment: {', '.join(equipment) or 'body weight only'}; notes: {p.notes[:500]}"
        if p else f"Training days per week: {days}; body weight only"
    )
    cand_lines = "\n".join(
        f"{e.id}: {e.name} [{', '.join(e.primary_muscles)}; {e.equipment}; {e.level}]" for e in candidates
    )
    raw = complete(
        f"User profile: {profile_line}\nUser request: {request or 'A balanced plan for my goal.'}\n\n"
        f"Candidate exercises:\n{cand_lines}",
        system=PLAN_SYSTEM, fast=False, max_tokens=5000, json_mode=True, temperature=0.3,
    )
    data = json.loads(raw)

    clean_days = []
    for d in data.get("days", [])[:7]:
        exercises = []
        for item in d.get("exercises", [])[:8]:
            ex = by_id.get(int(item.get("exercise_id", -1)))
            if not ex:
                continue  # the model referenced something not in the list — drop it
            exercises.append(
                {
                    "exercise_id": ex.id,
                    "name": ex.name,
                    "sets": max(1, min(int(item.get("sets", 3)), 6)),
                    "reps": str(item.get("reps", "8-12"))[:20],
                    "rest_sec": max(15, min(int(item.get("rest_sec", 90)), 300)),
                    "note": str(item.get("note", ""))[:200],
                }
            )
        if exercises:
            clean_days.append({"day": str(d.get("day", f"Day {len(clean_days) + 1}"))[:40],
                               "focus": str(d.get("focus", ""))[:80], "exercises": exercises})
    if not clean_days:
        raise ValueError("The plan came back empty — please try again.")

    # Only one active plan at a time.
    for old in db.scalars(select(WorkoutPlan).where(WorkoutPlan.user_id == user.id, WorkoutPlan.active)):
        old.active = False
    plan = WorkoutPlan(
        user_id=user.id,
        title=str(data.get("title") or "Your plan")[:200],
        description=str(data.get("description") or "")[:500],
        plan={"days": clean_days},
        active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def plan_out(db: Session, plan: WorkoutPlan) -> WorkoutPlanOut:
    ids = {e["exercise_id"] for d in plan.plan["days"] for e in d["exercises"]}
    exercises = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ids)))}
    days = [
        PlanDay(
            day=d["day"],
            focus=d["focus"],
            exercises=[
                PlanExercise(
                    **e,
                    exercise=ExerciseOut.model_validate(exercises[e["exercise_id"]])
                    if e["exercise_id"] in exercises else None,
                )
                for e in d["exercises"]
            ],
        )
        for d in plan.plan["days"]
    ]
    return WorkoutPlanOut(id=plan.id, title=plan.title, description=plan.description,
                          created_at=plan.created_at, days=days)


def log_set(db: Session, user: User, exercise_id: int, set_number: int, reps: int, weight_kg: float,
            plan_id: int | None, performed_on: date | None) -> WorkoutSet:
    ex = db.get(Exercise, exercise_id)
    if ex is None:
        raise ValueError("Unknown exercise")
    s = WorkoutSet(
        user_id=user.id, plan_id=plan_id, exercise_id=ex.id, exercise_name=ex.name,
        performed_on=performed_on or date.today(), set_number=set_number, reps=reps, weight_kg=weight_kg,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def last_session(db: Session, user: User, exercise_id: int) -> list[WorkoutSet]:
    """Sets from the most recent previous day this exercise was done (for 'beat last time')."""
    last_day = db.scalar(
        select(func.max(WorkoutSet.performed_on)).where(
            WorkoutSet.user_id == user.id, WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.performed_on < date.today(),
        )
    )
    if not last_day:
        return []
    return list(db.scalars(
        select(WorkoutSet).where(
            WorkoutSet.user_id == user.id, WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.performed_on == last_day,
        ).order_by(WorkoutSet.set_number)
    ))
