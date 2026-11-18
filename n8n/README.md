# n8n (Day 8)

## `food_nutrition_workflow.json`: our project workflow (same pattern as Lab 15)

`Webhook (GET /food-nutrition?food=apple)` → `Set food` → `Get nutrition` (HTTP Request to USDA FoodData Central) → `Format reply` (Code) → `Respond to Webhook`

It returns the calories, protein, fat, carbs, sugars, fibre and sodium per 100 g of a food, from **USDA FoodData Central**, the official US government food composition database. It fills a gap in our knowledge base: the guidelines say *what* to eat, and this says *how much is in it*.

1. In n8n: **+ → Workflow**. Open this file in VS Code, copy everything (**Ctrl+A**, **Ctrl+C**), click the canvas and paste (**Ctrl+V**). Or use **⋯ → Import from File**.
2. Save and turn it on (**Active** or **Publish**).
3. Test the **Production URL** in your browser with `?food=apple` at the end. You should see something like `Apples, ... (per 100 g): energy 52 kcal, ...`.
4. Put the URL in `.env` and in `.streamlit/secrets.toml` as `N8N_URL`. The Python agent then gets the `check_food` tool (Lab 16, Part B).

The API key in the HTTP node is `DEMO_KEY`, USDA's public demo key, which allows about 30 requests an hour. That's enough for the demo. For more, get a free key at [api.data.gov/signup](https://api.data.gov/signup/) and put it in the `api_key` parameter.

The agent sends food names in English (for example `dates`, `white rice`, `chicken breast`), because USDA's database is in English. The answer to the user is still in Arabic.

## `nutrition_agent_workflow.json`: n8n chat agent (Lab 16, Part A)

| Socket | Node | Same as in Python |
|---|---|---|
| Chat Model | OpenAI Chat Model, **Use Gateway credits** | `build_llm()` |
| Memory | Simple Memory, Context Window Length 10 | `InMemorySaver` + `thread_id`, MAX_MESSAGES = 10 |
| Tool | Calculator | `calculator` |
| Tool | `check_food` (HTTP Request Tool → the food-nutrition Production URL) | `check_food` |

After importing it, pick the credential in **OpenAI Chat Model** again, and paste the food-nutrition Production URL into **check_food**.

## `city_weather_workflow.json`

This is our original Lab 15 workflow, kept for reference. The project no longer uses it.

## Safety (from our Lab 16 worksheet)

The Production URL has no authentication, so anyone who gets it can call it. That uses up the n8n execution quota and the USDA key's rate limit. Keep the URL out of GitHub: it lives only in `.env` and `secrets.toml`, which are in `.gitignore`. The workflow only **reads** data, so no step needs a person to approve it.
