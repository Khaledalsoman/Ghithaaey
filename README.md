# غذائي | Ghithaaey

**An Arabic nutrition assistant that knows you, calculates your exact needs, and answers from official sources.**

You fill in your profile once. Ghithaaey then gives you your daily calories and macros, lets you log what you eat, and answers nutrition questions in Arabic, citing the Saudi Ministry of Health, WHO, FAO and SFDA. It doesn't give calorie targets to people under 18 or people with a health condition; it refers them to a doctor.

Final project for Tuwaiq Academy's *Developing Digital Products with Artificial Intelligence* program.
**Team:** Khaled Alqhtani · Ali Alzoghaibi · Amer Mobarki

> General nutrition information for healthy adults. Not medical advice.

---

## Why use it instead of a general chatbot

| A general chatbot | Ghithaaey |
|---|---|
| Asks for your age, height and weight every time | You fill in your profile once; every answer uses it |
| Estimates calories, and the number changes between answers | Exact numbers from a calculator (Mifflin-St Jeor + MOH/WHO guidelines) |
| Rarely says where an answer comes from | Answers from 31 official sources and names the source |
| Doesn't know what you ate today | Daily food log with USDA values; knows what's left of today's calories and protein |
| May give targets to anyone | No targets under 18 or with a health condition |

## The app

| Page | What the user does |
|---|---|
| **ملفك** (profile) | Age, sex, height, weight, activity, goal, target weight, health condition. Shown first to new users. |
| **خطتي** (my plan) | Calorie ring with what's left today, protein/carbs/fat, BMI and healthy weight range, BMR and maintenance calories, weeks to target, meal split, water, fibre, sugar/salt/saturated-fat limits. Calculated in Python, so it's instant. |
| **قيمة الأكل** (food values) | Pick a food (24 common Saudi foods, or any food in English) and the grams, see its values, add it to a meal in today's log. |
| **اسأل غذائي** (chat) | Ask anything. The agent already knows the profile and today's food. Shows which tools it used. |
| **المصادر** (sources) | Every official source, grouped by publisher, with links. |

Also: welcome message, example questions, a "new chat" button (deletes the profile and log), a "thinking" state, a friendly error message, Arabic right-to-left, our logo and theme.

## How it works

```
User ─► Streamlit app (app.py)
          │  ask(question, thread_id)
          ▼
        LangChain agent (assistant.py)
          │  model: Gemini 3.5 Flash-Lite      system prompt: config.json
          │  memory: InMemorySaver + thread_id, last 10 turns
          │  every turn: the saved profile and today's food log are added to the prompt
          │
          ├─► search_knowledge_base ─► vector_store.json (31 official sources)   rag.py
          ├─► nutrition_plan / save_profile ─► our calculator                      tools.py
          ├─► check_food ─► n8n webhook ─► USDA FoodData Central                   n8n/
          ├─► calculator
          └─► tavily_search (recent news only)
```

### Tools

| Tool | What it does | When the agent calls it |
|---|---|---|
| `search_knowledge_base` | RAG search, top 4 chunks with their source | Any nutrition fact question |
| `nutrition_plan` | BMI, BMR, calories, macros, water, limits, weeks to target | Calories, macros, losing or gaining weight |
| `save_profile` | Saves age, sex, height, weight, activity, goal for this chat | Whenever the user gives body data |
| `check_food` | Calls our n8n workflow → USDA values per 100 g | Calories or nutrients of a specific food |
| `calculator` | Safe arithmetic | Any math |
| `tavily_search` | Web search with links | Recent news only |

If a tool fails it returns `TOOL_FAILED` and the assistant says so instead of making up numbers.

### Knowledge base

- **31 official sources:** MOH (Arabic awareness pages and PDFs), WHO Arabic (healthy diet, obesity, salt), FAO Arabic, SFDA (food labels, caffeine, sugar and fat). The list is in `knowledge/web_sources.json`.
- **Pipeline:** download each page (BeautifulSoup; Tavily Extract when a site blocks us; PyPDF for PDFs) → clean the Arabic text → chunks of 400 characters, each with its topic title → multilingual MiniLM embeddings → `vector_store.json`.
- **About 643 chunks.** Retrieval test: 20 of 22 questions find the right source.
- **Not covered:** restaurant meals, medical diets. The assistant says «لست متأكداً», or uses `check_food` for a food's values.

### n8n workflow

`Webhook (GET ?food=…)` → `Set food` → `HTTP Request (USDA FoodData Central search)` → `Code (pick the best match, format per 100 g)` → `Respond to Webhook`.
It returns one line, e.g. *"Rice, white, cooked (per 100 g): energy … kcal, protein … g, … Source: USDA"*. The agent's `check_food` tool and the app's food page both use it. Files: `n8n/food_nutrition_workflow.json` (+ the Lab 16 agent version and our original Lab 15 weather workflow).

## Course coverage

| Lab | What we built | Where |
|---|---|---|
| 3-4 | System prompt: role, rules, tone, constraints, guardrails | `config.json` → `system_prompt` |
| 5-6 | Gemini through LangChain, terminal chat | `assistant.py` → `build_llm()` |
| 7-8 | Streamlit app, our theme | `app.py`, `.streamlit/config.toml`, `assets/` |
| 9-12 | Sources, Arabic cleaning, chunks, embeddings, RAG with sources | `build_knowledge_base.py`, `rag.py`, `knowledge/` |
| 13 | Tools + `create_agent` | `tools.py`, `assistant.py` |
| 14 | Memory: `InMemorySaver`, `thread_id`, trimming | `assistant.py`, `app.py` |
| 15-16 | n8n webhook workflow called from Python | `n8n/`, `tools.py` → `check_food` |
| Day 9 | Testing and improving | `tests/`, `results/` |

## Project structure

```
app.py                    Streamlit app (5 pages)
assistant.py              model, agent, memory, ask()
tools.py                  calculator, nutrition plan, profile, check_food (n8n), Tavily
rag.py                    retriever, knowledge tool, RAG chain
build_knowledge_base.py   download → clean → chunk → embed
config.json               system prompt, model and RAG settings, UI text
settings.py               paths + reading keys from .env or secrets.toml
knowledge/                sources list + downloaded pages and PDFs
vector_store.json         the built knowledge base
n8n/                      workflow JSON files
tests/                    evaluate.py, eval_retrieval.py, test_tools.py
results/                  baseline.csv, change1.csv
assets/, .streamlit/      logo, background, theme
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate             # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                                       # Mac/Linux: cp
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Put the same values in **both** `.env` (terminal) and `.streamlit/secrets.toml` (app):

| Setting | Value |
|---|---|
| `PROVIDER`, `MODEL` | `google`, `gemini-3.5-flash-lite` (or `openai` + `BASE_URL`, or `ollama`) |
| `API_KEY` | your Gemini key |
| `TAVILY_API_KEY` | optional, for web search |
| `N8N_URL` | the **Production** URL of the n8n workflow (`…/webhook/food-nutrition`) |

Both files are in `.gitignore`. Never commit them. To change the key, update both files and restart the app.

## Run

```bash
streamlit run app.py                # the app
python assistant.py                 # terminal chat (reset / quit)
python build_knowledge_base.py      # rebuild the knowledge base (only if sources change)
```

## Testing and improving (Day 9)

```bash
pytest                                           # each tool alone (7 tests, no key needed)
python tests/eval_retrieval.py                   # does search find the right source? (no key needed)
python tests/evaluate.py baseline                # 16 tests on the full assistant → results/baseline.csv
python tests/evaluate.py compare baseline change1
```

The 16 tests cover normal, vague, out-of-scope, not-in-the-data, prompt injection, medical, under-18, dialect, English, rude, the three tools and memory. Each answer gets automatic checks (must include, must not include, right tool) and an AI judge score (0-2).

| Run | Automatic checks | AI judge |
|---|---|---|
| baseline | 13 / 16 | 27 / 32 |
| change1 | 16 / 16 | 29 / 32 |

| Problem found | What we changed | Result |
|---|---|---|
| Memory test: activity not given, the model guessed "moderate" → 2,400 kcal | Prompt: «لا تخمّن مستوى النشاط… قل له إنك افترضت نشاطًا خفيفًا» | 2,077 kcal, and it says what it assumed (judge 1 → 2) |
| Rude message: Gemini blocked it → empty answer | `ask()`: an empty reply becomes a calm, friendly answer | judge 0 → 2 |
| "Big Mac meal" answered with per-100 g values | Prompt: say the values are per 100 g, not the whole meal | clearer answer |
| Calories test failed although the answer said "2,077" | Test fix: the checker ignores thousands commas and reads Arabic digits | test fix, not an assistant fix |
| Big Mac test expected only the knowledge base | Test fix: the food tool is also a right answer | test fix |

Two of the three new automatic passes came from fixing our tests. The memory pass and the judge points came from changing the assistant.

**Earlier improvements:**
- **Retrieval:** 14/20 → 18/20 (topic titles on chunks) → 20/22 (more official sources).
- **Memory:** trimming counted tool steps as messages, so the profile was lost after 2-3 questions. We now trim by turns and keep the profile separately.
- **Calories:** in Lab 5 the same question gave 1500-1600 kcal, then 1800-1900. The calculator tool makes it exact.
- **Embeddings:** Lab 13 loaded a different model than the one that built the store. Now there's one setting in `config.json`.

## Limits and next step

- **Food matching:** "100 g apples" once returned rose-apples. A better matching rule is in `n8n/food_nutrition_workflow.json`, not re-tested yet.
- **Data isn't saved:** the profile and food log live in memory. Restarting the app clears them.
- **Free limits:** the Gemini quota and the USDA `DEMO_KEY`.
- **Next step:** user accounts and a database, so the profile and food log last from day to day.

## Demo script

1. **Profile:** 25, male, 175 cm, 90 kg, light activity, lose weight, target 80 → plan: **2,077 kcal**, protein 122 g, about 20 weeks.
2. **Food:** add 200 g cooked rice to lunch → the ring and bars update.
3. **Easy:** «ما فوائد الفواكه والخضروات؟» → answer from the knowledge base with its source.
4. **Tricky:** «كم باقي لي سعرات اليوم؟ ووش أتعشى؟» → uses the profile, today's log and the calculator.
5. **Refuse:** set the health condition to diabetes, then ask «كم سعرة أحتاج عشان أنزل وزن؟» → no target, refers to a doctor.

Before presenting: start the app and ask one question 5 minutes early (the first load is slow), and check that the n8n workflow is published.
