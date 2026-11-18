"""The assistant: model + system prompt + tools + memory.

- Lab 5/6:  connect Gemini (Google AI), any OpenAI-compatible URL, or a local Ollama model.
- Lab 13:   create_agent with our tools.
- Lab 14:   InMemorySaver + thread_id, keeping the last MAX_MESSAGES = 10 messages.
- Day 7 guardrails: a step limit and a log of every tool call.
- Day 9: everything goes through one function, ask().

Terminal chat (like Lab 6 + Lab 14):  python assistant.py   (reset = new chat, quit = stop)
"""
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import before_model
from langchain_core.messages import RemoveMessage, trim_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from rag import build_knowledge_tool
from settings import CONFIG, get_secret
from tools import build_web_search, calculate_calories, calculator, check_weather


def build_llm():
    provider = get_secret("PROVIDER", CONFIG["provider"])
    model = get_secret("MODEL", CONFIG["model"])
    if provider == "ollama":  # Lab 5, option A: no key needed
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model)
    api_key = get_secret("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY is missing. Put it in .env or .streamlit/secrets.toml")
    if provider == "google":  # Labs 13 and 14: works with tool calling on Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    from langchain_openai import ChatOpenAI  # Lab 5, option B: OpenRouter or another OpenAI-compatible URL
    return ChatOpenAI(base_url=get_secret("BASE_URL", CONFIG["base_url"]), api_key=api_key, model=model)


def build_tools() -> list:
    tools = [build_knowledge_tool(), calculator, calculate_calories]
    if get_secret("N8N_URL"):
        tools.append(check_weather)
    web_search = build_web_search()
    if web_search:
        tools.append(web_search)
    return tools


@before_model
def keep_last_messages(state, runtime):
    """Lab 14: keep only the last MAX_MESSAGES messages (cost and speed)."""
    messages = state["messages"]
    if len(messages) <= CONFIG["max_messages"]:
        return None
    kept = trim_messages(messages, max_tokens=CONFIG["max_messages"], token_counter=len,
                         strategy="last", start_on="human", include_system=False)
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *kept]}


def build_agent():
    return create_agent(
        model=build_llm(),
        tools=build_tools(),
        system_prompt=CONFIG["system_prompt"],
        middleware=[keep_last_messages],
        checkpointer=InMemorySaver(),
    )


def new_thread_id() -> str:
    return str(uuid.uuid4())


def text_of(content) -> str:
    """Gemini returns a list of blocks ([{'type': 'text', 'text': ...}]), as seen in Labs 13-14."""
    if isinstance(content, list):
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return content


def ask(agent, question: str, thread_id: str) -> tuple[str, list[dict]]:
    """Send one question. Returns (answer, tool_log). Same thread_id = same chat (Lab 14)."""
    question = question.strip()
    if not question:
        return "اكتب سؤالك من فضلك.", []
    config = {"configurable": {"thread_id": thread_id},
              "recursion_limit": CONFIG["step_limit"] * 2 + 1}  # step limit: the loop always ends
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config)
    except GraphRecursionError:
        return "عذراً، احتجت خطوات كثيرة لهذا السؤال. جرّب تسأل بشكل أبسط.", []

    # Lab 13: print which tool was used for THIS question
    messages = result["messages"]
    last_human = max(i for i, m in enumerate(messages) if m.type == "human")
    tool_log = [{"tool": call["name"], "args": call["args"]}
                for m in messages[last_human:] if m.type == "ai"
                for call in (m.tool_calls or [])]
    return text_of(messages[-1].content), tool_log


if __name__ == "__main__":
    agent = build_agent()
    thread_id = new_thread_id()
    print(f"{CONFIG['assistant_name']}: {CONFIG['welcome']}\n({CONFIG['disclaimer']})\n")
    while True:
        question = input("You: ").strip()
        if question.lower() == "quit":
            break
        if question.lower() == "reset":
            thread_id = new_thread_id()
            continue
        try:
            answer, log = ask(agent, question, thread_id)
        except Exception:
            answer, log = CONFIG["friendly_error"], []
        for step in log:
            print("  Tool:", step["tool"], step["args"])
        print(f"{CONFIG['assistant_name']}: {answer}\n")
