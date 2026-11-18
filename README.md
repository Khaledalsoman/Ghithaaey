# غذائي | Ghithaaey

An Arabic AI nutrition specialist. It answers healthy-eating questions from Saudi Ministry of Health content and names its source. It calculates daily calories with a tool instead of guessing, remembers the conversation, and refuses medical consultations.

Capstone project for Tuwaiq Academy's *Developing Digital Products with AI* program.
**Team:** Khaled Alqhtani, Ali Alzoghaibi, Amer Mobarki

## How it works

```
User ─► Streamlit chat (app.py, Lab 7-8)
          │  ask(question, thread_id)
          ▼
        LangChain agent (assistant.py) ── our system prompt (config.json, Lab 3-4)
          │  memory: InMemorySaver + thread_id, last 10 messages (Lab 14)
          ├─► search_knowledge_base ─► vector_store.json ─► MOH pages (Lab 10-12)
          ├─► calculator (Lab 13), calculate_calories
          ├─► tavily_search (Lab 13)
          └─► check_weather ─► n8n webhook ─► wttr.in (Lab 15-16)
```

## Where each lab went

| Lab | What we did | In the project |
|---|---|---|
| 2 | Designed an assistant concept | This idea replaced our Lab 2 study-planner concept |
| 3-4 | System prompt, 2 constraints, 2 guardrails | `config.json` → `system_prompt` (our Lab 12/13 text, plus the Lab 4 rules) |
| 5-6 | Gemini through LangChain, key in `getpass`, chat loop | `assistant.py` → `build_llm()`, terminal chat; keys in `.env` |
| 7-8 | Streamlit screen, our dark colour theme | `app.py`, `config.json` (welcome, disclaimer, error, examples) |
| 9-10 | Planned sources; scraped the MOH page, Arabic `clean_text`, chunks of 200 | `knowledge/`, `build_knowledge_base.py` |
| 11 | Multilingual embeddings, merged short headings, `vector_store.json` | `build_knowledge_base.py`, `rag.py` |
| 12 | RAG chain with our Arabic rules and sources | `rag.py` → `build_rag_chain`, `answer_question` |
| 13 | Calculator, retriever tool, Tavily, `create_agent` | `tools.py`, `rag.py` → `build_knowledge_tool`, `assistant.py` |
| 14 | `InMemorySaver`, `thread_id`, MAX_MESSAGES = 10 | `assistant.py`, `app.py` (`st.session_state.thread_id`) |
| 15-16 | Weather webhook, n8n agent, Python calls the webhook | `n8n/`, `tools.py` → `check_weather` |
| Day 9 | Testing toolkit | `tests/evaluate.py` (uses the questions from our labs) |

## What we fixed from the labs

| Problem we saw | Fix |
|---|---|
| Lab 13 loaded `all-MiniLM-L6-v2` while Lab 11 built the store with the multilingual model, so the search returned unrelated chunks | One `embedding_model` setting in `config.json`, used when building and loading |
| Lab 13: the agent answered nutrition questions without calling any tool | The prompt now tells it to call `search_knowledge_base` first and answer only from it |
| Every chunk's source was `knowledge_base.json`, not the real page | Chunks keep the real file name, e.g. `moh_healthy_nutrition.txt` |
| Lab 12: "how much water per day?" → not sure, because water wasn't in our data | Added the MOH pages for water, breakfast, weight loss and fast food from our Lab 9 plan |
| Lab 5: the same question gave 1500-1600 kcal, then 1800-1900 kcal | `calculate_calories` tool gives one exact answer (Mifflin-St Jeor) |
| Lab 6 / Lab 8: no memory (our own "one improvement") | Lab 14 memory added to the app |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                       # for the terminal
cp .streamlit/secrets.toml.example .streamlit/secrets.toml # for the app
# put your Gemini key, Tavily key and n8n Production URL in both files
```

## Run

```bash
python build_knowledge_base.py      # Lab 10-11: clean, chunk, embed -> vector_store.json
pytest                              # test each tool alone
python rag.py "ما هي فوائد التغذية الصحية"   # Lab 12 chain, shows the context and sources
python assistant.py                 # terminal chat (reset / quit)
streamlit run app.py                # the app
python tests/evaluate.py baseline   # Day 9 tests, saved to results/
```

## Demo (60 seconds)

1. "انا طولي 175 و وزني 90 وعمري 25، ذكر، نشاطي خفيف، و ابي انحف" → `calculate_calories` gives 2077 kcal/day.
2. "وش أفطر؟" → remembers the goal and answers from the MOH source, naming it.
3. "كم ماء أشرب وأنا في جدة؟" → `check_weather` runs our n8n workflow (show it in **Executions**).
4. "عطني استشارة طبية في السمنة" → refuses and refers to a doctor.

## Disclaimer

General nutrition information only, not medical advice.
