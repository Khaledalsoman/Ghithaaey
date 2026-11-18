"""Our chat app: Lab 7 + Lab 8, with memory (Lab 14) and tools (Lab 13).

Run:  streamlit run app.py
Keys: .streamlit/secrets.toml (see secrets.toml.example)
"""
import streamlit as st

from assistant import ask, build_agent, new_thread_id
from settings import CONFIG

st.set_page_config(page_title=CONFIG["assistant_name"], page_icon="🥗")

# Lab 8: our colours. Plus right-to-left text for Arabic.
st.markdown("""
<style>
/* Main background */
.stApp {
    background-color: #0B1930;
    color: #FFFFFF;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #142B49;
}

/* All text */
.stApp p,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp li,
section[data-testid="stSidebar"] * {
    color: #FFFFFF;
}

/* Arabic: right to left */
.stApp p, .stApp li, .stApp h1, [data-testid="stChatMessageContent"] {
    direction: rtl;
    text-align: right;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background-color: #1D3658;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 14px;
}

/* Chat input */
[data-testid="stChatInput"] {
    background-color: #1D3658;
    border: 2px solid #4A90E2;
    border-radius: 12px;
}

[data-testid="stChatInput"] textarea {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF;
    caret-color: #FFFFFF;
    direction: rtl;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #CAD8EA !important;
    -webkit-text-fill-color: #CAD8EA;
}

/* Buttons */
.stButton > button {
    background-color: #2563EB;
    color: #FFFFFF;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

TOOL_LABELS = {
    "search_knowledge_base": "📚 قاعدة المعرفة",
    "calculator": "🧮 الآلة الحاسبة",
    "calculate_calories": "🔥 حساب السعرات",
    "check_food": "🍎 القيم الغذائية (n8n)",
    "tavily_search": "🌐 بحث الويب",
}


@st.cache_resource
def get_agent():
    return build_agent()


def show_tools(tool_log):
    if tool_log:
        with st.expander("الأدوات المستخدمة"):
            for step in tool_log:
                st.caption(f"{TOOL_LABELS.get(step['tool'], step['tool'])}: {step['args']}")


st.title(CONFIG["assistant_name"])
st.write(CONFIG["welcome"])

# Lab 14: one thread_id per chat, kept in st.session_state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = new_thread_id()
    st.session_state.messages = []

with st.sidebar:
    st.header("عن المساعد")
    st.write(CONFIG["disclaimer"])
    if st.button("محادثة جديدة", use_container_width=True):
        st.session_state.thread_id = new_thread_id()
        st.session_state.messages = []
        st.rerun()
    st.subheader("جرّب تسأل")  # Lab 7: example questions
    for example in CONFIG["examples"]:
        if st.button(example, use_container_width=True):
            st.session_state.pending = example

# Streamlit reruns this file on every click, so the chat is saved here (Lab 8)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        show_tools(message.get("tools"))

question = st.chat_input("اسألني أي شي عن التغذية") or st.session_state.pop("pending", None)

if question:
    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        with st.spinner("لحظة..."):
            answer, tool_log = ask(get_agent(), question, st.session_state.thread_id)
    except Exception:
        answer, tool_log = CONFIG["friendly_error"], []
    with st.chat_message("assistant"):
        st.write(answer)
        show_tools(tool_log)
    st.session_state.messages.append({"role": "assistant", "content": answer, "tools": tool_log})
