from betteru.services.calculator import full_nutrition_calculation as calc


def base(**kw):
    return {"age": 30, "sex": "female", "weight": 65, "height": 165, "activity": "moderate", "goal": "maintain"} | kw


def test_maintain_matches_tdee():
    r = calc(base())
    assert r["recommended_calories"] == r["tdee"]
    assert r["warnings"] == []


def test_cut_never_below_floor():
    r = calc(base(weight=50, height=155, activity="sedentary", goal="cut"))
    assert r["recommended_calories"] == 1200.0
    assert any("safe minimum" in w for w in r["warnings"])


def test_cut_deficit_capped_at_quarter_of_tdee():
    r = calc(base(sex="male", weight=60, height=170, activity="sedentary", goal="cut"))
    assert r["recommended_calories"] >= 0.75 * r["tdee"] - 0.1


def test_protein_uses_reference_weight_for_high_bmi():
    r = calc(base(sex="male", weight=150, height=175, activity="sedentary", goal="cut"))
    assert r["macros"]["protein_g"] < 200


def test_under_18_cannot_cut():
    r = calc(base(age=16, goal="cut"))
    assert r["goal_applied"] == "maintain"
    assert r["warnings"]


def test_underweight_cut_warns():
    r = calc(base(weight=45, height=170, goal="cut"))
    assert any("underweight" in w for w in r["warnings"])
