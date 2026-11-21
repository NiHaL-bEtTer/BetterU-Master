from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from betteru.models import MealEntry, User
from betteru.schemas import DaySummary, MealEntryOut, Totals
from betteru.services.foods import get_food, nutrients_for
from betteru.services.targets import targets_for


class FoodNotFound(Exception):
    pass


def add_entry(db: Session, user: User, food_id: int, grams: float, meal: str, eaten_on: date | None) -> MealEntry:
    food = get_food(db, food_id)
    if food is None:
        raise FoodNotFound(food_id)
    n = nutrients_for(food, grams)
    entry = MealEntry(
        user_id=user.id,
        eaten_on=eaten_on or date.today(),
        meal=meal,
        food_id=food.id,
        name=food.name,
        grams=grams,
        **n,
    )
    db.add(entry)
    return entry


def delete_entry(db: Session, user: User, entry_id: int) -> bool:
    result = db.execute(
        delete(MealEntry).where(MealEntry.id == entry_id, MealEntry.user_id == user.id)
    )
    return result.rowcount > 0


def entries_for_day(db: Session, user: User, day: date) -> list[MealEntry]:
    return list(
        db.scalars(
            select(MealEntry)
            .where(MealEntry.user_id == user.id, MealEntry.eaten_on == day)
            .order_by(MealEntry.created_at)
        )
    )


def totals(entries: list[MealEntry]) -> Totals:
    return Totals(
        kcal=round(sum(e.kcal for e in entries), 1),
        protein_g=round(sum(e.protein_g for e in entries), 1),
        carbs_g=round(sum(e.carbs_g for e in entries), 1),
        fat_g=round(sum(e.fat_g for e in entries), 1),
    )


def day_summary(db: Session, user: User, day: date) -> DaySummary:
    entries = entries_for_day(db, user, day)
    return DaySummary(
        date=day,
        entries=[MealEntryOut.model_validate(e) for e in entries],
        totals=totals(entries),
        targets=targets_for(user.profile),
    )


def recent_foods(db: Session, user: User, limit: int = 12) -> list[int]:
    """Most recently logged distinct foods, newest first."""
    rows = db.execute(
        select(MealEntry.food_id)
        .where(MealEntry.user_id == user.id, MealEntry.food_id.is_not(None))
        .group_by(MealEntry.food_id)
        .order_by(func.max(MealEntry.created_at).desc())
        .limit(limit)
    )
    return [r[0] for r in rows]
