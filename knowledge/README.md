# Knowledge base (Lab 9 plan → Lab 10 build)

**Assistant:** AI Nutrition specialist

## 5 questions our users will ask (Lab 9)

1. How do I lose weight?
2. What foods are healthy?
3. How much water should I drink daily?
4. Is fast food unhealthy?
5. What should I eat for breakfast?

## Sources and quality check (Lab 9)

| Source | Type | Trusted? Why? | Keep? |
|---|---|---|---|
| Ministry of Health | Web pages | Yes, Saudi ministry | Y |
| World Health Organization | Web page | Yes, authorized world organization | Y |
| National Institutes of Health | Web page | Yes, authorized | Y |
| Healthy food guidelines for health practitioners | Document | Yes, Ministry of Health | Y |
| Social media content | — | **Rejected**: not trusted | N |

## What is built so far

| File | From | Answers questions |
|---|---|---|
| `moh_healthy_nutrition.txt` | Lab 10 (MOH page, already scraped and cleaned) | 2, 4 (partly), calories, fibre, fats, grains |
| `moh_healthy_eating_habits.txt` | downloaded by `build_knowledge_base.py` | 3, 5 |
| `moh_healthy_food_choices.txt` | downloaded by `build_knowledge_base.py` | 1, 4 |

Lab 12 showed the gap: "كم كمية الماء التي يجب شربها يوميًا؟" got "لست متأكداً" because water was not in our one MOH page. The two new MOH pages cover water, breakfast, weight loss and fast food from the Lab 9 plan.

## How to add a source

- **Web page:** add `{"file": "name.txt", "url": "..."}` to `web_sources.json`.
- **Text or PDF:** put a `.txt` or `.pdf` file in this folder (one topic per file).

Then run `python build_knowledge_base.py` again. If a site blocks the download, copy the page text into a `.txt` file here by hand.
