# Knowledge base (Lab 9 plan → Lab 10 build)

**Assistant:** AI Nutrition specialist. Only official sources: Saudi Ministry of Health (MOH), Saudi Food and Drug Authority (SFDA), World Health Organization (WHO).

## Topic coverage

| Topic | Source files | Publisher |
|---|---|---|
| Healthy eating, calories, fibre, fats, grains | `moh_healthy_nutrition.txt` (our Lab 10 page), `who_healthy_diet_ar.txt` | MOH, WHO |
| Weight loss and gain | `moh_losing_gaining_weight.txt`, `moh_weight_loss_tips.pdf`, `moh_calorie_guide.txt` | MOH |
| Water | `moh_water_and_exercise.txt`, `moh_healthy_eating_habits.txt` | MOH |
| Breakfast and eating habits | `moh_healthy_eating_habits.txt`, `moh_your_food_health_or_disease.pdf` | MOH |
| Fast food and sugary drinks | `moh_healthy_nutrition.txt`, `moh_sugary_drinks.txt` | MOH |
| Salt | `who_healthy_diet_ar.txt`, `moh_hypertension_diet.txt` | WHO, MOH |
| Ramadan (suhoor, iftar, fasting) | `moh_ramadan_suhoor.txt`, `moh_ramadan_iftar.txt`, `moh_ramadan_healthy_lifestyle.pdf`, `moh_fasting_nutrition.pdf` | MOH |
| Athletes, protein supplements | `moh_athletes_nutrition.txt`, `moh_protein_supplements.txt` | MOH |
| Diets: keto, vegetarian | `moh_keto_diet.txt`, `moh_vegetarian_diet.txt` | MOH |
| Foods: fish, milk | `moh_fish.txt`, `moh_milk.txt` | MOH |
| Students' nutrition, poor nutrition | `moh_students_nutrition.txt`, `moh_poor_nutrition.txt` | MOH |
| Food labels | `sfda_nutrition_label_guide.pdf` | SFDA |
| Food safety at home | `moh_food_care_guidelines.txt` | MOH |
| Saudi dietary guidelines (Healthy Food Palm) | `moh_healthy_food_palm.pdf` | MOH (2012) |

All URLs are in `web_sources.json`. `python build_knowledge_base.py` downloads each one once and keeps a copy in this folder.

## Five checks (Lab 9)

- **Trusted:** only .gov.sa and who.int.
- **Up to date:** MOH pages show "آخر تعديل" at the bottom. The Healthy Food Palm is from 2012, so it's still the national guideline but old; prefer newer pages when they disagree.
- **Relevant:** each file is one topic.
- **Clear and complete:** check the sample line that the build prints for each file.
- **Allowed:** public government information.

Rejected: social media content, because it isn't trusted (Lab 9).

## After building, check quality

The build prints one sample line per file. If a sample shows menu text or broken Arabic (common with PDFs), open that file. Then either delete it, or copy the article text by hand into a `.txt` file with the same name. After that, run `python build_knowledge_base.py` and `python tests/eval_retrieval.py` again.

If a site blocks the download (`FAILED`), open the URL in your browser, copy the article text into a `.txt` file with the name from `web_sources.json`, and build again.
