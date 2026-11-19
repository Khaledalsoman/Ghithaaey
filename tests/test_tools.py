"""Test every tool alone before giving it to the AI (Day 7). Run: pytest"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import PROFILES, bmi, bmr, calculator, check_food, nutrition_plan, save_profile  # noqa: E402


def cfg(thread):
    return {"configurable": {"thread_id": thread}}


def test_calculator_lab13():
    assert calculator.invoke({"a": 4873, "b": 29, "operation": "multiply"}) == "141317.0"
    assert calculator.invoke({"a": 1, "b": 0, "operation": "divide"}) == "Cannot divide by zero."
    assert "Use add" in calculator.invoke({"a": 1, "b": 2, "operation": "power"})


def test_bmi_and_bmr():
    assert bmi(90, 175) == 29.4
    assert bmr(90, 175, 25, "male") == 1874  # 10*90 + 6.25*175 - 5*25 + 5


def test_lab5_question_full_plan():
    # Lab 5: 175 cm, 90 kg, wants to lose weight. The model alone gave 1500-1600 or 1800-1900.
    out = nutrition_plan.invoke({"weight_kg": 90, "height_cm": 175, "age": 25, "sex": "male",
                                 "activity": "light", "goal": "lose", "target_weight_kg": 80}, config=cfg("a"))
    assert "2077 kcal/day" in out          # 1874 * 1.375 = 2577, minus 500
    assert "protein 122 g" in out          # 1.6 g/kg of the weight at BMI 25 (76.6 kg)
    assert "about 20 weeks" in out         # 10 kg at 0.5 kg/week
    assert "salt under 5 g" in out


def test_profile_is_remembered_in_the_thread():
    PROFILES.clear()
    save_profile.invoke({"weight_kg": 90, "height_cm": 175}, config=cfg("b"))
    assert nutrition_plan.invoke({}, config=cfg("b")).startswith("MISSING")
    out = nutrition_plan.invoke({"age": 25, "sex": "male", "goal": "lose"}, config=cfg("b"))
    assert "2077 kcal/day" in out          # weight and height came from the saved profile
    assert nutrition_plan.invoke({}, config=cfg("other")).startswith("MISSING")  # threads are separate


def test_minimum_calories_guardrail():
    out = nutrition_plan.invoke({"weight_kg": 45, "height_cm": 150, "age": 30, "sex": "female",
                                 "activity": "sedentary", "goal": "lose"}, config=cfg("c"))
    assert "1200 kcal/day (raised to the safe minimum)" in out


def test_under_18_guardrail_lab10_question():
    # Lab 10 test question: "i am 15 years old and my weight is 70 and my height is 165"
    out = nutrition_plan.invoke({"weight_kg": 70, "height_cm": 165, "age": 15, "sex": "male",
                                 "goal": "maintain"}, config=cfg("d"))
    assert out.startswith("UNDER_18")


def test_food_tool_without_n8n(monkeypatch):
    monkeypatch.delenv("N8N_URL", raising=False)
    assert check_food.invoke({"food": "apple"}).startswith(("TOOL_UNAVAILABLE", "TOOL_FAILED"))


def test_health_condition_blocks_targets():
    config = {"configurable": {"thread_id": "condition-test"}}
    answer = nutrition_plan.invoke({"age": 25, "sex": "male", "weight_kg": 80, "height_cm": 175,
                                    "goal": "lose", "condition": "diabetes"}, config)
    assert answer.startswith("MEDICAL_CONDITION")
