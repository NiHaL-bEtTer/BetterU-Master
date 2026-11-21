from betteru.models import Profile
from betteru.schemas import Targets
from betteru.services.calculator import full_nutrition_calculation


def targets_for(profile: Profile | None) -> Targets | None:
    if profile is None:
        return None
    result = full_nutrition_calculation(
        {
            "age": profile.age,
            "sex": profile.sex,
            "weight": profile.weight_kg,
            "height": profile.height_cm,
            "activity": profile.activity,
            "goal": profile.goal,
        }
    )
    return Targets(**result)
