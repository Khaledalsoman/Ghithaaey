"""Test every tool alone before giving it to the AI (Day 7). Run: pytest"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import bmi, bmr, calculate_calories, calculator, check_weather  # noqa: E402


def test_calculator_lab13():
    assert calculator.invoke({"a": 4873, "b": 29, "operation": "multiply"}) == "141317.0"
    assert calculator.invoke({"a": 1, "b": 0, "operation": "divide"}) == "Cannot divide by zero."
    assert "Use add" in calculator.invoke({"a": 1, "b": 2, "operation": "power"})


def test_bmi_and_bmr():
    assert bmi(90, 175) == 29.4
    assert bmr(90, 175, 25, "male") == 1874  # 10*90 + 6.25*175 - 5*25 + 5


def test_lab5_question_gets_one_answer():
    # Lab 5: 175 cm, 90 kg, wants to lose weight. The model alone gave 1500-1600 or 1800-1900.
    out = calculate_calories.invoke({"weight_kg": 90, "height_cm": 175, "age": 25, "sex": "male",
                                     "activity": "light", "goal": "lose"})
    assert "2077 kcal/day" in out  # 1874 * 1.375 = 2577, minus 500


def test_minimum_calories_guardrail():
    out = calculate_calories.invoke({"weight_kg": 45, "height_cm": 150, "age": 30, "sex": "female",
                                     "activity": "sedentary", "goal": "lose"})
    assert "1200 kcal/day" in out


def test_under_18_guardrail_lab10_question():
    # Lab 10 test question: "i am 15 years old and my weight is 70 and my height is 165"
    out = calculate_calories.invoke({"weight_kg": 70, "height_cm": 165, "age": 15, "sex": "male",
                                     "activity": "light", "goal": "maintain"})
    assert out.startswith("UNDER_18")


def test_weather_tool_without_n8n(monkeypatch):
    monkeypatch.delenv("N8N_URL", raising=False)
    assert check_weather.invoke({"city": "Jeddah"}).startswith(("TOOL_UNAVAILABLE", "TOOL_FAILED"))
