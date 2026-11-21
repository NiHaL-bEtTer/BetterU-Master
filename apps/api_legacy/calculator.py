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

# A cut never removes more than this share of TDEE...
MAX_DEFICIT_FRACTION = 0.25
# ...and never goes below these commonly cited minimum intakes (kcal/day).
MIN_CALORIES = {"male": 1500, "female": 1200}


def calculate_goal_calories(tdee, goal, sex="female") -> float:
    goal = goal.lower().strip()
    if goal not in GOAL_ADJUSTMENTS:
        valid = ", ".join(GOAL_ADJUSTMENTS.keys())
        raise ValueError(f"Invalid goal. Choose from: {valid}")

    adjustment = GOAL_ADJUSTMENTS[goal]
    if adjustment < 0:
        adjustment = max(adjustment, -MAX_DEFICIT_FRACTION * tdee)
        floor = MIN_CALORIES.get(sex.lower().strip(), 1200)
        # Never push the target above maintenance just to satisfy the floor.
        return round(float(max(tdee + adjustment, min(floor, tdee))), 1)
    return round(tdee + adjustment, 1)


# ---------------------------------------------------------------------------
# Macros
# ---------------------------------------------------------------------------

PROTEIN_TARGETS = {
    "bulk":     2.0,
    "maintain": 1.8,
    "cut":      2.4,
}


# Protein is dosed per kg of body weight. For BMI >= 30 that over-estimates
# need (fat mass needs little protein), so dose against the weight at BMI 25.
PROTEIN_REFERENCE_BMI = 25
# Protein never takes more than this share of total calories.
MAX_PROTEIN_FRACTION = 0.35


def protein_reference_weight(weight_kg, height_cm=None) -> float:
    if not height_cm:
        return weight_kg
    bmi = weight_kg / (height_cm / 100) ** 2
    if bmi < 30:
        return weight_kg
    return PROTEIN_REFERENCE_BMI * (height_cm / 100) ** 2


def calculate_macros(weight_kg, calorie_target, goal, height_cm=None) -> dict:
    if weight_kg <= 0:
        raise ValueError("Weight must be a positive number.")
    if calorie_target <= 0:
        raise ValueError("Calorie target must be a positive number.")

    ref_weight = protein_reference_weight(weight_kg, height_cm)
    protein_g  = PROTEIN_TARGETS[goal] * ref_weight
    protein_g  = round(min(protein_g, MAX_PROTEIN_FRACTION * calorie_target / 4), 1)
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
    recommended_calories = calculate_goal_calories(tdee, goal, user_data["sex"])
    macros               = calculate_macros(weight_kg, recommended_calories, goal, height_cm)

    warnings = []
    if goal == "cut" and bmi < 18.5:
        warnings.append(
            "BMI is below 18.5 (underweight). A calorie deficit is not recommended "
            "without guidance from a doctor or registered dietitian."
        )
    if goal == "cut" and recommended_calories > tdee + GOAL_ADJUSTMENTS["cut"]:
        warnings.append(
            "The deficit was reduced to keep intake at a safe minimum."
        )

    return {
        "bmi":                  bmi,
        "bmr":                  bmr,
        "tdee":                 tdee,
        "recommended_calories": recommended_calories,
        "macros":               macros,
        "warnings":             warnings,
    }