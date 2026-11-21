from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from betteru.deps import DB, CurrentUser
from betteru.models import WorkoutPlan, WorkoutSet
from betteru.schemas import SetIn, SetOut, WorkoutPlanOut, WorkoutRequest
from betteru.services import workouts

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/plan", response_model=WorkoutPlanOut | None)
def active_plan(db: DB, user: CurrentUser):
    plan = db.scalar(
        select(WorkoutPlan).where(WorkoutPlan.user_id == user.id, WorkoutPlan.active)
        .order_by(WorkoutPlan.created_at.desc())
    )
    return workouts.plan_out(db, plan) if plan else None


@router.post("/plan", response_model=WorkoutPlanOut, status_code=201)
def create_plan(body: WorkoutRequest, db: DB, user: CurrentUser):
    try:
        plan = workouts.generate_plan(db, user, body.request)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    except Exception:  # noqa: BLE001 — LLM/JSON failures
        raise HTTPException(502, "Couldn't generate a plan right now. Please try again.") from None
    return workouts.plan_out(db, plan)


@router.post("/sets", response_model=SetOut, status_code=201)
def log_set(body: SetIn, db: DB, user: CurrentUser):
    try:
        return workouts.log_set(db, user, body.exercise_id, body.set_number, body.reps,
                                body.weight_kg, body.plan_id, body.performed_on)
    except ValueError as e:
        raise HTTPException(404, str(e)) from None


@router.get("/sets/today", response_model=list[SetOut])
def sets_today(db: DB, user: CurrentUser):
    return db.scalars(
        select(WorkoutSet).where(WorkoutSet.user_id == user.id, WorkoutSet.performed_on == date.today())
        .order_by(WorkoutSet.created_at)
    ).all()


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(set_id: int, db: DB, user: CurrentUser):
    s = db.get(WorkoutSet, set_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Set not found")
    db.delete(s)
    db.commit()


@router.get("/exercises/{exercise_id}/last", response_model=list[SetOut])
def last_time(exercise_id: int, db: DB, user: CurrentUser):
    return workouts.last_session(db, user, exercise_id)
