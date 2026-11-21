"""Weight trend and adaptive TDEE.

Daily weight jumps around with water and food volume, so we show a 7-day
moving average. With ~2 weeks of weigh-ins and food logs we can estimate the
user's *real* maintenance calories from energy balance:

    TDEE ≈ average daily intake − (weight change per day × 7700 kcal/kg)
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from betteru.models import MealEntry, User, WeightEntry
from betteru.schemas import ProgressOut, WeightPoint
from betteru.services.targets import targets_for

KCAL_PER_KG = 7700
MIN_WEIGH_INS = 8
MIN_LOGGED_DAYS = 10
WINDOW_DAYS = 14


def moving_average(points: list[tuple[date, float]], days: int = 7) -> list[WeightPoint]:
    out = []
    for i, (d, w) in enumerate(points):
        window = [wt for (dd, wt) in points[: i + 1] if (d - dd).days < days]
        out.append(WeightPoint(date=d, weight_kg=w, trend_kg=round(sum(window) / len(window), 2)))
    return out


def _slope_per_day(points: list[tuple[date, float]]) -> float:
    """Least-squares slope (kg/day)."""
    xs = [(d - points[0][0]).days for d, _ in points]
    ys = [w for _, w in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denom


def progress_for(db: Session, user: User, today: date | None = None) -> ProgressOut:
    today = today or date.today()
    rows = db.execute(
        select(WeightEntry.measured_on, WeightEntry.weight_kg)
        .where(WeightEntry.user_id == user.id, WeightEntry.measured_on >= today - timedelta(days=180))
        .order_by(WeightEntry.measured_on)
    ).all()
    points = [(r[0], r[1]) for r in rows]

    since = today - timedelta(days=WINDOW_DAYS)
    daily = db.execute(
        select(MealEntry.eaten_on, func.sum(MealEntry.kcal))
        .where(MealEntry.user_id == user.id, MealEntry.eaten_on > since, MealEntry.eaten_on <= today)
        .group_by(MealEntry.eaten_on)
    ).all()
    # Ignore days that are clearly partial logs (under 800 kcal).
    logged = [kcal for _, kcal in daily if kcal and kcal >= 800]

    targets = targets_for(user.profile)
    formula_tdee = targets.tdee if targets else None

    recent = [p for p in points if p[0] > since]
    estimated = None
    if len(recent) >= MIN_WEIGH_INS and len(logged) >= MIN_LOGGED_DAYS:
        intake = sum(logged) / len(logged)
        estimated = round(intake - _slope_per_day(recent) * KCAL_PER_KG)

    if estimated:
        message = f"Based on your last {WINDOW_DAYS} days, your maintenance is about {estimated:,.0f} kcal/day."
    else:
        need_w = max(0, MIN_WEIGH_INS - len(recent))
        need_d = max(0, MIN_LOGGED_DAYS - len(logged))
        message = (
            "Keep logging to unlock your personal maintenance estimate: "
            f"{need_w} more weigh-ins and {need_d} more fully logged days in the next two weeks."
        )

    return ProgressOut(
        weights=moving_average(points),
        logged_days_last_14=len(logged),
        estimated_tdee=estimated,
        formula_tdee=formula_tdee,
        message=message,
    )
