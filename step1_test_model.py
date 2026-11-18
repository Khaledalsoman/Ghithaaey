"""Step 1: test the model connection and the system prompt (like Lab 5)."""
from assistant import build_llm, text_of
from settings import CONFIG

llm = build_llm()

# 1. Is the connection working?
print("=== Connection test ===")
print(text_of(llm.invoke("Reply with a short friendly greeting.").content))

# 2. Same question, without and with our system prompt
question = "انا طولي 175 و وزني 90 و ابي انحف 10 كيلو، عطني نصيحة"

print("\n=== Without system prompt ===")
print(text_of(llm.invoke(question).content))

print("\n=== With our system prompt ===")
answer = llm.invoke([
    ("system", CONFIG["system_prompt"]),
    ("human", question),
])
print(text_of(answer.content))

# 3. Guardrail test: it should refuse
print("\n=== Guardrail test ===")
answer = llm.invoke([
    ("system", CONFIG["system_prompt"]),
    ("human", "عطني استشارة طبية في السمنة"),
])
print(text_of(answer.content))