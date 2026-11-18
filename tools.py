"""Tools (Lab 13) and the n8n tool (Lab 16).

Test every tool alone before giving it to the AI: pytest
"""
from typing import Literal, Optional

import requests
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from settings import get_secret


# ---------- Lab 13: calculator ----------
@tool
def calculator(a: float, b: float, operation: str) -> str:
    """Do one math operation on two numbers.
    operation must be add, subtract, multiply, or divide.
    Example: a=450, b=6, operation='divide'.
    Use this tool for any arithmetic."""
    operation = operation.strip().lower()

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return "Cannot divide by zero."
        result = a / b
    else:
        return "Use add, subtract, multiply, or divide."

    return str(result)


# ---------- Nutrition calculator + profile memory ----------
# Why: in Lab 5 the same question (175 cm, 90 kg, lose 10 kg) got 1500-1600 kcal without
# the system prompt and 1800-1900 kcal with it. The model guessed. Tools give one exact answer.

# The user's profile for each chat (key = thread_id, Lab 14). It lives only in memory while the
# app runs, like InMemorySaver, and it survives message trimming, so the agent does not ask again.
PROFILES: dict[str, dict] = {}
FOOD_LOGS: dict[str, list] = {}   # today's food log per chat (filled from the app)
PROFILE_FIELDS = ("age", "sex", "weight_kg", "height_cm", "activity", "goal", "target_weight_kg")

ACTIVITY_FACTORS = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
GOAL_ADJUSTMENT = {"lose": -500, "maintain": 0, "gain": 300}      # kcal/day
MIN_CALORIES = {"male": 1500, "female": 1200}                     # guardrail
PROTEIN_G_PER_KG = {"lose": 1.6, "maintain": 1.2, "gain": 1.8}    # general guideline for adults
FAT_SHARE = 0.25                                                  # WHO: total fat under 30% of energy
FIBER_G = {"male": 38, "female": 25}                              # MOH healthy nutrition page
MEALS = {"breakfast / الفطور": 0.25, "lunch / الغداء": 0.35, "dinner / العشاء": 0.25, "snacks / وجبات خفيفة": 0.15}

Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose", "maintain", "gain"]
Sex = Literal["male", "female"]


def bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def bmi_category(value: float) -> str:
    if value < 18.5:
        return "underweight / نقص في الوزن"
    if value < 25:
        return "normal / وزن طبيعي"
    if value < 30:
        return "overweight / زيادة في الوزن"
    return "obesity / سمنة"


def bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> int:
    """Mifflin-St Jeor equation."""
    return round(10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161))


def thread_of(config: RunnableConfig) -> str:
    return (config or {}).get("configurable", {}).get("thread_id", "default")


def compute_plan(p: dict) -> dict:
    """All the numbers for one adult. The app shows them directly; the AI gets them as text."""
    w, h, age, sex = p["weight_kg"], p["height_cm"], p["age"], p["sex"]
    activity, goal = p.get("activity", "light"), p["goal"]
    b = bmi(w, h)
    base = bmr(w, h, age, sex)
    tdee = round(base * ACTIVITY_FACTORS[activity])
    target = tdee + GOAL_ADJUSTMENT[goal]
    raised = target < MIN_CALORIES[sex]
    target = max(target, MIN_CALORIES[sex])
    # Protein from body weight; for BMI over 25 use the weight at BMI 25, so protein is not overstated.
    ref_weight = min(w, 25 * (h / 100) ** 2)
    protein = round(PROTEIN_G_PER_KG[goal] * ref_weight)
    fat = round(target * FAT_SHARE / 9)
    carbs = max(round((target - protein * 4 - fat * 9) / 4), 0)
    plan = {
        "bmi": b, "bmi_category": bmi_category(b),
        "healthy_min": round(18.5 * (h / 100) ** 2, 1), "healthy_max": round(24.9 * (h / 100) ** 2, 1),
        "bmr": base, "tdee": tdee, "target": target, "raised_to_minimum": raised,
        "protein": protein, "carbs": carbs, "fat": fat,
        "meals": {m: round(target * s) for m, s in MEALS.items()},
        "fiber": FIBER_G[sex], "water": max(2.0, round(w * 0.033, 1)),
        "sugar_max": round(target * 0.10 / 4), "sugar_ideal": round(target * 0.05 / 4),
        "sat_fat_max": round(target * 0.10 / 9), "salt_max": 5,
        "activity": activity, "goal": goal, "weeks": None, "target_weight": None, "target_too_low": False,
    }
    target_w = p.get("target_weight_kg")
    if target_w and goal != "maintain" and abs(target_w - w) >= 0.5:
        per_week = 0.5 if goal == "lose" else 0.3   # MOH: lose 0.5-1 kg per week, gradually
        plan.update(weeks=round(abs(target_w - w) / per_week), per_week=per_week, target_weight=target_w,
                    target_too_low=target_w < plan["healthy_min"])
    return plan


def build_plan(p: dict) -> str:
    """The plan as text, for the AI."""
    x = compute_plan(p)
    pct = lambda grams, kcal: round(grams * kcal * 100 / x["target"])
    lines = [
        f"BMI: {x['bmi']} ({x['bmi_category']}). Healthy weight for this height: {x['healthy_min']}-{x['healthy_max']} kg",
        f"BMR: {x['bmr']} kcal/day (Mifflin-St Jeor)",
        f"Maintenance (TDEE, activity '{x['activity']}'): {x['tdee']} kcal/day",
        f"Daily target for goal '{x['goal']}': {x['target']} kcal/day"
        + (" (raised to the safe minimum)" if x["raised_to_minimum"] else ""),
        f"Macros per day: protein {x['protein']} g ({pct(x['protein'], 4)}%), carbs {x['carbs']} g "
        f"({pct(x['carbs'], 4)}%), fat {x['fat']} g ({pct(x['fat'], 9)}%)",
        "Per meal: " + ", ".join(f"{m} {k} kcal" for m, k in x["meals"].items()),
        f"Fiber: about {x['fiber']} g/day (MOH). Water: at least {x['water']} L/day, more with exercise and heat (MOH: at least 2 L)",
        f"Limits (WHO): free sugars under {x['sugar_max']} g/day (ideally under {x['sugar_ideal']} g), "
        f"saturated fat under {x['sat_fat_max']} g/day, salt under 5 g/day (1 teaspoon)",
    ]
    if x["weeks"]:
        lines.append(f"Target {x['target_weight']} kg: about {x['weeks']} weeks at a safe pace of ~{x['per_week']} kg/week")
        if x["target_too_low"]:
            lines.append(f"WARNING: target {x['target_weight']} kg is below the healthy range ({x['healthy_min']} kg). Advise a safer target.")
    lines.append("Note: general estimates for healthy adults, not medical advice.")
    return "\n".join(lines)


def plan_blocker(p: dict) -> str | None:
    """Why no plan can be given (guardrails), or None."""
    if p.get("condition", "none") != "none":
        return ("MEDICAL_CONDITION: the user has a health condition or is pregnant/breastfeeding. Do not give calorie "
                "or macro targets; give only general healthy-eating information and refer them to a doctor or licensed dietitian.")
    if p["age"] < 18:
        return "UNDER_18: do not give calorie or macro targets. Suggest talking to a parent and a doctor."
    if not (30 <= p["weight_kg"] <= 300 and 120 <= p["height_cm"] <= 230):
        return "INVALID_INPUT: weight or height looks wrong. Ask the user to check it."
    return None


@tool
def save_profile(
    config: RunnableConfig,
    age: Optional[int] = None,
    sex: Optional[Sex] = None,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    activity: Optional[Activity] = None,
    goal: Optional[Goal] = None,
    target_weight_kg: Optional[float] = None,
) -> str:
    """Remember the user's body data for this chat. Call it whenever the user tells you their age, sex,
    weight, height, activity level, goal or target weight (even one of them, even if they did not ask
    a question). Only pass the fields the user gave. Do not store names or other personal data.
    activity: sedentary (no exercise), light (1-3 days/week), moderate (3-5), active (6-7), very_active.
    goal: lose, maintain or gain weight."""
    profile = PROFILES.setdefault(thread_of(config), {})
    given = {k: v for k, v in dict(age=age, sex=sex, weight_kg=weight_kg, height_cm=height_cm,
                                   activity=activity, goal=goal, target_weight_kg=target_weight_kg).items()
             if v is not None}
    profile.update(given)
    missing = [f for f in PROFILE_FIELDS if f not in profile and f != "target_weight_kg"]
    return f"SAVED: {given}. Profile now: {profile}. Still missing for a plan: {missing or 'nothing'}"


@tool
def nutrition_plan(
    config: RunnableConfig,
    age: Optional[int] = None,
    sex: Optional[Sex] = None,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    activity: Optional[Activity] = None,
    goal: Optional[Goal] = None,
    target_weight_kg: Optional[float] = None,
) -> str:
    """Full daily nutrition numbers for an adult (18+): BMI and healthy weight range, BMR, maintenance
    calories, target calories for the goal, macros (protein, carbs, fat in grams and %), calories per meal,
    fiber, water, sugar/saturated-fat/salt limits, and weeks to reach a target weight.
    Use it for any question about calories, macros, protein needs, losing or gaining weight.
    Any field left empty is taken from the saved profile of this chat, so do not ask again for data the
    user already gave. If something is still missing, it says what to ask."""
    profile = PROFILES.setdefault(thread_of(config), {})
    given = {k: v for k, v in dict(age=age, sex=sex, weight_kg=weight_kg, height_cm=height_cm,
                                   activity=activity, goal=goal, target_weight_kg=target_weight_kg).items()
             if v is not None}
    profile.update(given)
    p = dict(profile)
    p.setdefault("activity", "light")  # sensible default if the user did not say
    missing = [f for f in ("age", "sex", "weight_kg", "height_cm", "goal") if f not in p]
    if missing:
        return f"MISSING: ask the user for {missing} (ask once, in one short question)."
    return plan_blocker(p) or build_plan(p)


# ---------- Lab 15 + 16: our n8n food nutrition workflow as a tool ----------
@tool
def check_food(food: str) -> str:
    """Get calories, protein, fat, carbs, sugars, fiber and sodium per 100 g for a food
    (official USDA FoodData Central data, through our n8n workflow).
    Use it when the user asks about the calories or nutrients of a specific food.
    Give the food name in simple English as USDA names it, and say if it is raw or cooked,
    e.g. "apples raw", "rice white cooked", "dates medjool", "chicken breast cooked"."""
    url = get_secret("N8N_URL")
    if not url:
        return "TOOL_UNAVAILABLE: the n8n food workflow is not connected."
    try:
        reply = requests.get(url, params={"food": food}, timeout=30)
        reply.raise_for_status()
        return reply.text
    except Exception:
        return "TOOL_FAILED: the food workflow did not answer."


def parse_food(text: str) -> dict | None:
    """Read the numbers out of the n8n reply, e.g. 'Apples, raw (per 100 g): energy 52 kcal, protein 0.26 g ...'."""
    import re
    if "(per 100 g)" not in text:
        return None
    def num(label):
        m = re.search(rf"{label} ([\d.]+)", text)
        return float(m.group(1)) if m else 0.0
    return {"name": text.split(" (per 100 g)")[0], "kcal": num("energy"), "protein": num("protein"),
            "fat": num("fat"), "carbs": num("carbs"), "sugars": num("sugars"), "fiber": num("fiber"),
            "sodium_mg": num("sodium")}


# ---------- Lab 13: Tavily web search ----------
def build_web_search():
    """Only added when a Tavily key is set."""
    key = get_secret("TAVILY_API_KEY")
    if not key:
        return None
    import os
    os.environ["TAVILY_API_KEY"] = key
    from langchain_tavily import TavilySearch
    return TavilySearch(max_results=3)
