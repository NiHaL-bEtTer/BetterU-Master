"""Request and response shapes for the HTTP API.

These also feed the OpenAPI schema that generates the web app's TypeScript types.
"""

from datetime import date as Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Sex = Literal["male", "female"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["cut", "maintain", "bulk"]
Diet = Literal["none", "vegetarian", "vegan", "pescatarian", "halal", "kosher"]
Meal = Literal["breakfast", "lunch", "dinner", "snack"]
Units = Literal["metric", "imperial"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(default="", max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class UserOut(ORM):
    id: int
    email: str
    name: str
    has_profile: bool


# ── Profile & targets ─────────────────────────────────────────────────────


class ProfileIn(BaseModel):
    age: int = Field(ge=13, le=100)
    sex: Sex
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=25, le=300)
    activity: Activity
    goal: Goal
    units: Units = "metric"
    diet: Diet = "none"
    allergies: list[str] = Field(default_factory=list, max_length=20)
    equipment: list[str] = Field(default_factory=list, max_length=20)
    training_days: int = Field(default=3, ge=1, le=7)
    notes: str = Field(default="", max_length=4000)
    name: str | None = Field(default=None, max_length=100)  # saved on the user; optional


class ProfileOut(ProfileIn, ORM):
    pass


class Macros(BaseModel):
    protein_g: float
    fat_g: float
    carbs_g: float


class Targets(BaseModel):
    bmi: float
    bmr: float
    tdee: float
    recommended_calories: float
    macros: Macros
    goal_applied: Goal
    warnings: list[str]


class ProfileWithTargets(BaseModel):
    profile: ProfileOut
    targets: Targets


# ── Foods ─────────────────────────────────────────────────────────────────


class PortionOut(ORM):
    id: int
    description: str
    grams: float


class FoodOut(ORM):
    id: int
    name: str
    category: str
    source: str
    barcode: str | None = None
    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sat_fat_g: float | None = None
    sodium_mg: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_d_ug: float | None = None
    portions: list[PortionOut] = []


# ── Food log ──────────────────────────────────────────────────────────────


class MealItemIn(BaseModel):
    food_id: int
    grams: float = Field(gt=0, le=5000)


class MealEntryIn(MealItemIn):
    meal: Meal
    eaten_on: Date | None = None  # defaults to today


class MealEntriesIn(BaseModel):
    meal: Meal
    eaten_on: Date | None = None
    items: list[MealItemIn] = Field(min_length=1, max_length=30)


class MealEntryOut(ORM):
    id: int
    eaten_on: Date
    meal: Meal
    food_id: int | None
    name: str
    grams: float
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Totals(BaseModel):
    kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0


class DayTotals(Totals):
    date: Date


class DaySummary(BaseModel):
    date: Date
    entries: list[MealEntryOut]
    totals: Totals
    targets: Targets | None


# ── Progress ──────────────────────────────────────────────────────────────


class WeightIn(BaseModel):
    weight_kg: float = Field(ge=25, le=300)
    measured_on: Date | None = None


class WeightPoint(BaseModel):
    date: Date
    weight_kg: float
    trend_kg: float  # 7-day moving average


class ProgressOut(BaseModel):
    weights: list[WeightPoint]
    logged_days_last_14: int
    estimated_tdee: float | None  # from intake vs weight trend, needs ~2 weeks of data
    formula_tdee: float | None
    message: str


# ── Workouts ──────────────────────────────────────────────────────────────


class ExerciseOut(ORM):
    id: int
    name: str
    category: str
    level: str
    equipment: str
    primary_muscles: list[str]
    secondary_muscles: list[str]
    instructions: list[str]
    images: list[str]


class WorkoutRequest(BaseModel):
    request: str = Field(default="", max_length=1000)


class PlanExercise(BaseModel):
    exercise_id: int
    name: str
    sets: int
    reps: str
    rest_sec: int
    note: str = ""
    exercise: ExerciseOut | None = None


class PlanDay(BaseModel):
    day: str
    focus: str
    exercises: list[PlanExercise]


class WorkoutPlanOut(ORM):
    id: int
    title: str
    description: str
    created_at: datetime
    days: list[PlanDay]


class SetIn(BaseModel):
    exercise_id: int
    set_number: int = Field(ge=1, le=20)
    reps: int = Field(ge=0, le=200)
    weight_kg: float = Field(default=0, ge=0, le=1000)
    plan_id: int | None = None
    performed_on: Date | None = None


class SetOut(ORM):
    id: int
    exercise_id: int | None
    exercise_name: str
    performed_on: Date
    set_number: int
    reps: int
    weight_kg: float


# ── Chat ──────────────────────────────────────────────────────────────────


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class Source(BaseModel):
    id: str  # "S1", "F12" — what Alden cites in its answer
    title: str
    url: str = ""
    kind: Literal["food", "document", "web"]


class ChatAction(BaseModel):
    type: Literal["log_meal", "build_workout"]
    label: str
    payload: dict


class ChatMessageOut(ORM):
    id: int
    role: Literal["user", "assistant"]
    content: str
    sources: list[Source]
    actions: list[ChatAction]
    video_id: str | None
    rating: int | None
    created_at: datetime


class RatingIn(BaseModel):
    rating: Literal[-1, 0, 1]
