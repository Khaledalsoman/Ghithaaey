# n8n (Day 8)

If our Lab 15 and Lab 16 workflows are still in our n8n account, use those. These files are copies you can import with **Workflows → ⋯ → Import from File**.

## `city_weather_workflow.json` (Lab 15)

`Webhook (GET /city-weather)` → `Set city` (`{{ $json.query.city }}`) → `Get weather` (`https://wttr.in/{{ $json.city }}?format=3`) → `Respond to Webhook` (`{{ $json.data }}`)

Our results in Lab 15: Riyadh +20°C, Jeddah +30°C, Abha +17°C.

1. Turn the workflow on (Active or Publish).
2. Copy the **Production URL** (it has `/webhook/`, not `/webhook-test/`).
3. Put it in `.env` and `.streamlit/secrets.toml` as `N8N_URL`. The Python agent then gets the `check_weather` tool (Lab 16, Part B).

**How it fits a nutrition assistant:** the agent uses the weather for hydration advice. For example, for "كم ماء أشرب وأنا في جدة؟" it checks Jeddah's temperature, then answers from the knowledge base.

## `nutrition_agent_workflow.json` (Lab 16, Part A)

The same agent we built in Lab 16, with a nutrition system message:

| Socket | Node | Same as in Python |
|---|---|---|
| Chat Model | OpenAI Chat Model, **Use Gateway credits**, gpt-5-mini | `build_llm()` |
| Memory | Simple Memory, Context Window Length 10 | `InMemorySaver` + `thread_id`, MAX_MESSAGES = 10 |
| Tool | Calculator | `calculator` |
| Tool | check_weather (HTTP Request Tool → Lab 15 Production URL, `city` defined by the model) | `check_weather` |

After importing, pick the credential in **OpenAI Chat Model** again, and paste the Lab 15 Production URL into **check_weather**.

## Safety (from our Lab 16 worksheet)

The Production URL has no authentication, so anyone who gets it can call it. That uses up the n8n execution quota and Gateway credits, and could get us rate-limited by wttr.in. Keep the URL out of GitHub: it lives only in `.env` and `secrets.toml`, which are in `.gitignore`. For a real product, add Header Auth on the Webhook node.
