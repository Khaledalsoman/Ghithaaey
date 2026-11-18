"""Tools (Lab 13) and the n8n tool (Lab 16).

Test every tool alone before giving it to the AI: pytest
"""
from typing import Literal

import requests
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


# ---------- New: daily calories ----------
# Why: in Lab 5 the same question (175 cm, 90 kg, lose 10 kg) got 1500-1600 kcal without
# the system prompt and 1800-1900 kcal with it. The model guessed. A tool gives one exact answer.
ACTIVITY_FACTORS = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
GOAL_ADJUSTMENT = {"lose": -500, "maintain": 0, "gain": 300}
MIN_CALORIES = {"male": 1500, "female": 1200}  # guardrail


def bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> int:
    """Mifflin-St Jeor equation."""
    return round(10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161))


@tool
def calculate_calories(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Literal["male", "female"],
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"],
    goal: Literal["lose", "maintain", "gain"],
) -> str:
    """Calculate BMI, BMR and a safe daily calorie target for an adult (18+).
    Use it when the user gives weight, height and age and asks how many calories they need,
    or wants to lose or gain weight. If activity is not given, use 'light'.
    activity: sedentary (no exercise), light (1-3 days/week), moderate (3-5), active (6-7), very_active."""
    if age < 18:
        return "UNDER_18: do not give a calorie target. Suggest talking to a parent and a doctor."
    if not (30 <= weight_kg <= 300 and 120 <= height_cm <= 230):
        return "INVALID_INPUT: weight or height looks wrong. Ask the user to check it."
    b = bmi(weight_kg, height_cm)
    base = bmr(weight_kg, height_cm, age, sex)
    tdee = round(base * ACTIVITY_FACTORS[activity])
    target = max(tdee + GOAL_ADJUSTMENT[goal], MIN_CALORIES[sex])
    return (f"BMI: {b}\nBMR: {base} kcal/day\nMaintenance: {tdee} kcal/day\n"
            f"Daily target for goal '{goal}': {target} kcal/day\nMethod: Mifflin-St Jeor equation.")


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
