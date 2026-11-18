"""RAG retrieval test (Day 6 + Day 9): does the search find the right source?

    python tests/eval_retrieval.py

For each question we know which file should answer it. The test passes if that file
is in the top K chunks. No model and no key needed, only vector_store.json.
Change ONE setting (k, max_chars, a source), rebuild, run again, and compare the score.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag import get_vector_store  # noqa: E402
from settings import CONFIG, KNOWLEDGE_DIR  # noqa: E402

# question -> files that contain the answer (any one is enough)
QUESTIONS = [
    ("ما هي فوائد الألياف؟", ["moh_healthy_nutrition.txt"]),
    ("كم سعرة يحتاج الرجل في اليوم؟", ["moh_healthy_nutrition.txt", "moh_calorie_guide.txt"]),
    ("كم كوب ماء أشرب يوميًا؟", ["moh_water_and_exercise.txt", "moh_healthy_eating_habits.txt", "moh_students_nutrition.txt"]),
    ("وش أفطر عشان يكون فطوري صحي؟", ["moh_healthy_eating_habits.txt", "moh_school_breakfast.txt", "moh_your_food_health_or_disease.pdf", "moh_students_nutrition.txt"]),
    ("كيف أنزل وزني بطريقة صحية؟", ["moh_losing_gaining_weight.txt", "moh_weight_loss_tips.pdf", "moh_calorie_guide.txt"]),
    ("كيف أزيد وزني؟", ["moh_losing_gaining_weight.txt"]),
    ("هل الوجبات السريعة مضرة؟", ["moh_healthy_nutrition.txt", "moh_your_food_health_or_disease.pdf"]),
    ("هل المشروبات الغازية والعصائر المحلاة مضرة؟", ["moh_sugary_drinks.txt"]),
    ("كم الحد اليومي للملح؟", ["who_healthy_diet_ar.txt", "moh_hypertension_diet.txt"]),
    ("وش آكل في السحور؟", ["moh_ramadan_suhoor.txt", "moh_ramadan_healthy_lifestyle.pdf", "moh_fasting_nutrition.pdf"]),
    ("كيف أفطر بشكل صحي في رمضان؟", ["moh_ramadan_iftar.txt", "moh_ramadan_healthy_lifestyle.pdf", "moh_fasting_nutrition.pdf"]),
    ("وش أفضل أكل للرياضيين؟", ["moh_athletes_nutrition.txt"]),
    ("هل مكملات البروتين آمنة؟", ["moh_protein_supplements.txt"]),
    ("هل حمية الكيتو مفيدة؟", ["moh_keto_diet.txt"]),
    ("وش فوائد السمك؟", ["moh_fish.txt"]),
    ("هل الحليب مفيد؟", ["moh_milk.txt"]),
    ("أبي أصير نباتي، وش لازم أنتبه له؟", ["moh_vegetarian_diet.txt"]),
    ("كيف أقرأ البطاقة الغذائية على المنتج؟", ["sfda_nutrition_label_guide.pdf"]),
    ("كيف أحفظ الأكل بطريقة سليمة؟", ["moh_food_care_guidelines.txt"]),
    ("وش هي النخلة الغذائية الصحية؟", ["moh_healthy_food_palm_ar.pdf", "moh_healthy_food_palm.pdf"]),
    ("كم كوب قهوة مسموح في اليوم؟", ["sfda_caffeine_ar.txt", "sfda_caffeine_sugar_fat_guide.pdf"]),
    ("متى يعتبر الشخص سمين؟", ["who_obesity_ar.txt", "moh_overweight_obesity.txt", "moh_weight_loss_tips.pdf"]),
]


def main():
    store = get_vector_store()
    k = CONFIG["k"]
    stem = lambda name: name.rsplit(".", 1)[0]
    have = {stem(p.name) for p in KNOWLEDGE_DIR.iterdir() if p.stat().st_size > 300}
    passed = tested = 0
    for question, expected in QUESTIONS:
        if not any(stem(f) in have for f in expected):
            print(f"[SKIP] {question}  (source not downloaded: {expected[0]})")
            continue
        tested += 1
        results = store.similarity_search_with_score(question, k=k)
        found = [doc.metadata["source"] for doc, _ in results]
        ok = any(stem(f) in {stem(x) for x in found} for f in expected)
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {question}\n        top: {found[0]} ({results[0][1]:.2f})"
              + ("" if ok else f" | expected: {expected[0]}"))

    # A question the knowledge base cannot answer: the best score should be low.
    doc, score = store.similarity_search_with_score("من فاز بكأس العالم 2022؟", k=1)[0]
    print(f"\n[INFO] off-topic question best score: {score:.2f} (lower is better)")
    print(f"\nRetrieval score: {passed}/{tested} questions found the right source in the top {k}")


if __name__ == "__main__":
    main()
