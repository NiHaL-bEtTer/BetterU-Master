from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from betteru.deps import DB, CurrentUser
from betteru.models import WeightEntry
from betteru.schemas import ProgressOut, WeightIn
from betteru.services.progress import progress_for

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def get_progress(db: DB, user: CurrentUser):
    return progress_for(db, user)


@router.post("/weight", response_model=ProgressOut)
def log_weight(body: WeightIn, db: DB, user: CurrentUser):
    day = body.measured_on or date.today()
    entry = db.scalar(select(WeightEntry).where(WeightEntry.user_id == user.id, WeightEntry.measured_on == day))
    if entry:
        entry.weight_kg = body.weight_kg
    else:
        db.add(WeightEntry(user_id=user.id, measured_on=day, weight_kg=body.weight_kg))
    # The newest weigh-in also updates the profile, so targets stay current.
    if user.profile and day >= date.today():
        user.profile.weight_kg = body.weight_kg
    db.commit()
    return progress_for(db, user)
