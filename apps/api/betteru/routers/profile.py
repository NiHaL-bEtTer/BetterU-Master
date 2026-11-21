from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from betteru.deps import DB, CurrentUser
from betteru.models import ChatMessage, MealEntry, Profile, WeightEntry, WorkoutPlan, WorkoutSet
from betteru.schemas import ProfileIn, ProfileOut, ProfileWithTargets, Targets
from betteru.security import clear_session_cookie
from betteru.services.calculator import full_nutrition_calculation
from betteru.services.targets import targets_for

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileWithTargets)
def get_profile(user: CurrentUser):
    if user.profile is None:
        raise HTTPException(404, "No profile yet")
    return _with_targets(user)


def _with_targets(user) -> ProfileWithTargets:
    profile = ProfileOut.model_validate(user.profile).model_copy(update={"name": user.name})
    return ProfileWithTargets(profile=profile, targets=targets_for(user.profile))


@router.put("", response_model=ProfileWithTargets)
def save_profile(body: ProfileIn, user: CurrentUser, db: DB):
    allergies = sorted({a.strip().lower() for a in body.allergies if a.strip()})
    equipment = sorted({e.strip().lower() for e in body.equipment if e.strip()})
    data = body.model_dump(exclude={"name"}) | {"allergies": allergies, "equipment": equipment}
    if body.name is not None:
        user.name = body.name.strip()
    if user.profile is None:
        user.profile = Profile(user_id=user.id, **data)
    else:
        for k, v in data.items():
            setattr(user.profile, k, v)
    # Keep the weight history in sync with the profile weight.
    from datetime import date
    existing = db.scalar(select(WeightEntry).where(WeightEntry.user_id == user.id, WeightEntry.measured_on == date.today()))
    if existing:
        existing.weight_kg = body.weight_kg
    else:
        db.add(WeightEntry(user_id=user.id, measured_on=date.today(), weight_kg=body.weight_kg))
    db.commit()
    db.refresh(user)
    return _with_targets(user)


@router.post("/preview-targets", response_model=Targets)
def preview_targets(body: ProfileIn):
    """Targets for unsaved form values (used live during onboarding)."""
    return Targets(**full_nutrition_calculation({
        "age": body.age, "sex": body.sex, "weight": body.weight_kg, "height": body.height_cm,
        "activity": body.activity, "goal": body.goal,
    }))


@router.get("/export")
def export_data(user: CurrentUser, db: DB):
    """Everything we store about the user, as JSON (data portability)."""
    def rows(model):
        return [
            {c.name: getattr(r, c.name) for c in model.__table__.columns if c.name not in {"user_id"}}
            for r in db.scalars(select(model).where(model.user_id == user.id))
        ]
    return {
        "user": {"email": user.email, "name": user.name, "created_at": user.created_at},
        "profile": ProfileOut.model_validate(user.profile).model_dump() if user.profile else None,
        "weights": rows(WeightEntry),
        "meals": rows(MealEntry),
        "workout_plans": rows(WorkoutPlan),
        "workout_sets": rows(WorkoutSet),
        "chat_messages": rows(ChatMessage),
    }


@router.delete("/account", status_code=204)
def delete_account(user: CurrentUser, db: DB, response: Response):
    """Permanently delete the account and all of its data (cascades)."""
    db.delete(user)
    db.commit()
    clear_session_cookie(response)
