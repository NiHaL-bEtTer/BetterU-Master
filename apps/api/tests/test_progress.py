from datetime import date, timedelta
from types import SimpleNamespace

from betteru.services.progress import _slope_per_day, moving_average


def test_moving_average_smooths():
    d0 = date(2026, 1, 1)
    pts = [(d0 + timedelta(days=i), w) for i, w in enumerate([70, 71, 69, 70, 72, 70, 69])]
    out = moving_average(pts)
    assert out[-1].trend_kg == round(sum(w for _, w in pts) / 7, 2)


def test_slope_detects_loss():
    d0 = date(2026, 1, 1)
    pts = [(d0 + timedelta(days=i), 80 - 0.1 * i) for i in range(14)]
    assert abs(_slope_per_day(pts) + 0.1) < 1e-9


def test_adaptive_tdee(user_client, db):
    from betteru.models import MealEntry, User, WeightEntry
    from betteru.services.progress import progress_for

    user = db.query(User).one()
    today = date.today()
    db.query(WeightEntry).delete()
    for i in range(14):
        day = today - timedelta(days=13 - i)
        db.add(WeightEntry(user_id=user.id, measured_on=day, weight_kg=70 - 0.05 * i))  # -0.35 kg/week
        db.add(MealEntry(user_id=user.id, eaten_on=day, meal="lunch", name="x", grams=1, kcal=2000))
    db.commit()
    p = progress_for(db, SimpleNamespace(id=user.id, profile=user.profile))
    # 2000 kcal intake + 0.05 kg/day * 7700 = 2385
    assert p.estimated_tdee == 2385
