from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from betteru.deps import DB, CurrentUser
from betteru.models import FavoriteFood, Food, MealEntry
from betteru.schemas import DaySummary, DayTotals, FoodOut, MealEntriesIn, MealEntryIn, MealEntryOut
from betteru.services import food_log
from betteru.services.foods import food_from_barcode, get_food, search_foods_with_fallback

router = APIRouter(tags=["foods"])


@router.get("/foods/search", response_model=list[FoodOut])
def food_search(db: DB, user: CurrentUser, q: str = Query(min_length=1, max_length=100)):
    return search_foods_with_fallback(db, q, limit=15)


@router.get("/foods/barcode/{code}", response_model=FoodOut)
def food_by_barcode(code: str, db: DB, user: CurrentUser):
    food = food_from_barcode(db, code)
    if not food:
        raise HTTPException(404, "Product not found for that barcode")
    return food


@router.get("/foods/recent", response_model=list[FoodOut])
def recent(db: DB, user: CurrentUser):
    ids = food_log.recent_foods(db, user)
    foods = {f.id: f for f in db.scalars(select(Food).where(Food.id.in_(ids)).options(selectinload(Food.portions)))}
    return [foods[i] for i in ids if i in foods]


@router.get("/foods/favorites", response_model=list[FoodOut])
def favorites(db: DB, user: CurrentUser):
    return db.scalars(
        select(Food).join(FavoriteFood, FavoriteFood.food_id == Food.id)
        .where(FavoriteFood.user_id == user.id).options(selectinload(Food.portions))
    ).all()


@router.put("/foods/{food_id}/favorite", status_code=204)
def add_favorite(food_id: int, db: DB, user: CurrentUser):
    if not db.get(Food, food_id):
        raise HTTPException(404, "Food not found")
    if not db.scalar(select(FavoriteFood).where(FavoriteFood.user_id == user.id, FavoriteFood.food_id == food_id)):
        db.add(FavoriteFood(user_id=user.id, food_id=food_id))
        db.commit()


@router.delete("/foods/{food_id}/favorite", status_code=204)
def remove_favorite(food_id: int, db: DB, user: CurrentUser):
    db.execute(delete(FavoriteFood).where(FavoriteFood.user_id == user.id, FavoriteFood.food_id == food_id))
    db.commit()


@router.get("/foods/{food_id}", response_model=FoodOut)
def food_detail(food_id: int, db: DB, user: CurrentUser):
    food = get_food(db, food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


# ── Food log ──────────────────────────────────────────────────────────────


@router.get("/log/week", response_model=list[DayTotals])
def week(db: DB, user: CurrentUser, end: date | None = None, days: int = Query(default=7, ge=1, le=31)):
    """Daily totals for the last `days` days ending on `end` (default today), oldest first."""
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    rows = db.execute(
        select(MealEntry.eaten_on, func.sum(MealEntry.kcal), func.sum(MealEntry.protein_g),
               func.sum(MealEntry.carbs_g), func.sum(MealEntry.fat_g))
        .where(MealEntry.user_id == user.id, MealEntry.eaten_on >= start, MealEntry.eaten_on <= end)
        .group_by(MealEntry.eaten_on)
    ).all()
    by_day = {r[0]: r for r in rows}
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        r = by_day.get(d)
        out.append(DayTotals(date=d, kcal=round(r[1], 1) if r else 0, protein_g=round(r[2], 1) if r else 0,
                             carbs_g=round(r[3], 1) if r else 0, fat_g=round(r[4], 1) if r else 0))
    return out


@router.get("/log/{day}", response_model=DaySummary)
def get_day(day: date, db: DB, user: CurrentUser):
    return food_log.day_summary(db, user, day)


@router.post("/log", response_model=MealEntryOut, status_code=201)
def add_to_log(body: MealEntryIn, db: DB, user: CurrentUser):
    try:
        entry = food_log.add_entry(db, user, body.food_id, body.grams, body.meal, body.eaten_on)
    except food_log.FoodNotFound:
        raise HTTPException(404, "Food not found") from None
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/log/batch", response_model=list[MealEntryOut], status_code=201)
def add_many_to_log(body: MealEntriesIn, db: DB, user: CurrentUser):
    """Used by Alden's 'Log meal' button: several foods in one tap."""
    try:
        entries = [food_log.add_entry(db, user, i.food_id, i.grams, body.meal, body.eaten_on) for i in body.items]
    except food_log.FoodNotFound:
        db.rollback()
        raise HTTPException(404, "One of the foods no longer exists") from None
    db.commit()
    for e in entries:
        db.refresh(e)
    return entries


@router.delete("/log/{entry_id}", status_code=204)
def delete_from_log(entry_id: int, db: DB, user: CurrentUser):
    if not food_log.delete_entry(db, user, entry_id):
        raise HTTPException(404, "Entry not found")
    db.commit()
