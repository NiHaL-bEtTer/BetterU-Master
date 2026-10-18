"""
calculator.py
-------------
Pure deterministic nutrition calculator.
No AI, no external dependencies — standard Python only.

Formulas: Mifflin-St Jeor BMR, standard activity multipliers.
Supports metric (kg / cm) and imperial (lbs / inches) input.
"""

# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

def _to_metric(weight, height, unit_system: str):
    unit_system = unit_system.lower().strip()
    if unit_system not in ("metric", "imperial"):
        raise ValueError("unit_system must be 'metric' or 'imperial'.")
    if unit_system == "imperial":
        return weight * 0.45359237, height * 2.54
    return float(weight), float(height)


# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg, height_cm) -> float:
    if weight_kg <= 0:
        raise ValueError("Weight must be a positive number.")
    if height_cm <= 0:
        raise ValueError("Height must be a positive number.")
    return round(weight_kg / (height_cm / 100) ** 2, 1)


# ---------------------------------------------------------------------------
# BMR  (Mifflin-St Jeor)
# ---------------------------------------------------------------------------

def calculate_bmr(age, sex, weight_kg, height_cm) -> float:
    if age <= 0:
        raise ValueError("Age must be a positive number.")
    if weight_kg <= 0:
        raise ValueError("Weight must be a positive number.")
    if height_cm <= 0:
        raise ValueError("Height must be a positive number.")

    sex = sex.lower().strip()
    if sex not in ("male", "female"):
        raise ValueError("Sex must be 'male' or 'female'.")

    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return round(bmr + (5 if sex == "male" else -161), 1)


# ---------------------------------------------------------------------------
# TDEE
# ---------------------------------------------------------------------------

ACTIVITY_FACTORS = {
    "sedentary":   1.2,
    "light":       1.375,
    "moderate":    1.55,
    "active":      1.725,
    "very_active": 1.9,
}


def calculate_tdee(bmr, activity_level) -> float:
    activity_level = activity_level.lower().strip()
    if activity_level not in ACTIVITY_FACTORS:
        valid = ", ".join(ACTIVITY_FACTORS.keys())
        raise ValueError(f"Invalid activity level. Choose from: {valid}")
    return round(bmr * ACTIVITY_FACTORS[activity_level], 1)


# ---------------------------------------------------------------------------
# Goal calories
# ---------------------------------------------------------------------------

GOAL_ADJUSTMENTS = {
    "bulk":     400,
    "maintain":   0,
    "cut":     -500,
}


def calculate_goal_calories(tdee, goal) -> float:
    goal = goal.lower().strip()
    if goal not in GOAL_ADJUSTMENTS:
        valid = ", ".join(GOAL_ADJUSTMENTS.keys())
        raise ValueError(f"Invalid goal. Choose from: {valid}")
    return round(tdee + GOAL_ADJUSTMENTS[goal], 1)


# ---------------------------------------------------------------------------
# Macros
# ---------------------------------------------------------------------------

PROTEIN_TARGETS = {
    "bulk":     2.0,
    "maintain": 1.8,
    "cut":      2.4,
}


def calculate_macros(weight_kg, calorie_target, goal) -> dict:
    if weight_kg <= 0:
        raise ValueError("Weight must be a positive number.")
    if calorie_target <= 0:
        raise ValueError("Calorie target must be a positive number.")

    protein_g = round(PROTEIN_TARGETS[goal] * weight_kg, 1)
    fat_g     = round((0.30 * calorie_target) / 9, 1)
    carbs_g   = round(max((calorie_target - protein_g * 4 - fat_g * 9) / 4, 0), 1)

    return {"protein_g": protein_g, "fat_g": fat_g, "carbs_g": carbs_g}


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def full_nutrition_calculation(user_data: dict) -> dict:
    """
    Run a complete nutrition calculation.

    Required keys:
        age         (int)   - years
        sex         (str)   - 'male' or 'female'
        weight      (float) - kg (metric) or lbs (imperial)
        height      (float) - cm (metric) or inches (imperial)
        activity    (str)   - sedentary | light | moderate | active | very_active
        goal        (str)   - bulk | maintain | cut

    Optional keys:
        unit_system (str)   - 'metric' (default) or 'imperial'

    Returns:
        dict: {
            'bmi':                  float,
            'bmr':                  float,
            'tdee':                 float,
            'recommended_calories': float,
            'macros': {
                'protein_g': float,
                'fat_g':     float,
                'carbs_g':   float,
            }
        }
    """
    required = {"age", "sex", "weight", "height", "activity", "goal"}
    missing  = required - user_data.keys()
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

    unit_system = user_data.get("unit_system", "metric")
    goal        = user_data["goal"].lower().strip()

    weight_kg, height_cm = _to_metric(
        user_data["weight"], user_data["height"], unit_system
    )

    bmi                  = calculate_bmi(weight_kg, height_cm)
    bmr                  = calculate_bmr(user_data["age"], user_data["sex"], weight_kg, height_cm)
    tdee                 = calculate_tdee(bmr, user_data["activity"])
    recommended_calories = calculate_goal_calories(tdee, goal)
    macros               = calculate_macros(weight_kg, recommended_calories, goal)

    return {
        "bmi":                  bmi,
        "bmr":                  bmr,
        "tdee":                 tdee,
        "recommended_calories": recommended_calories,
        "macros":               macros,
    }