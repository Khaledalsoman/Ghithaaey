"""RAG: our Lab 12 chain, and the Lab 13 retriever tool.

Try the chain alone:  python rag.py "ما هي فوائد التغذية الصحية"
"""
import sys
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore

from settings import CONFIG, VECTOR_STORE_JSON

# Lab 12: our RAG rules
RAG_RULES = """
أجب فقط بناءً على المعلومات الواردة في السياق أدناه.
إذا لم تكن الإجابة موجودة في السياق، فقل: "لست متأكداً. لم أتمكن من العثور على هذه المعلومة في قاعدة بياناتي."
اجعل الإجابة موجزة، واذكر اسم الملف المصدري.
"""


@lru_cache(maxsize=1)
def get_embeddings():
    # Labs 11 and 12 used this multilingual model. Lab 13 loaded all-MiniLM-L6-v2 by mistake,
    # which is why its search returned unrelated chunks. One setting now, used everywhere.
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=CONFIG["embedding_model"])


@lru_cache(maxsize=1)
def get_vector_store() -> InMemoryVectorStore:
    if not VECTOR_STORE_JSON.exists():
        raise FileNotFoundError("vector_store.json is missing. Run: python build_knowledge_base.py")
    return InMemoryVectorStore.load(str(VECTOR_STORE_JSON), get_embeddings())


def get_retriever():
    return get_vector_store().as_retriever(search_kwargs={"k": CONFIG["k"]})


def format_docs(docs) -> str:
    return "\n\n".join(f"[{doc.metadata['source']}] {doc.page_content}" for doc in docs)


def build_knowledge_tool():
    """Lab 13: our retriever as a tool, with our Arabic description."""
    return create_retriever_tool(
        get_retriever(),
        "search_knowledge_base",
        "ابحث في قاعدة المعرفة عن التغذية الصحية والعناصر الغذائية وفوائدها. "
        "استخدمها لأي سؤال عن الغذاء الصحي، السعرات، الألياف، الدهون، الفواكه والخضراوات. "
        "كل نتيجة تبدأ باسم الملف المصدر بين قوسين.",
        # Show the source with each chunk, so the agent can name it (Day 6: show your sources)
        document_prompt=PromptTemplate.from_template("[{source}] {page_content}"),
    )


def build_rag_chain(llm):
    """Lab 12: prompt | llm | StrOutputParser."""
    safe_system = (CONFIG["system_prompt"].strip() + "\n" + RAG_RULES.strip()).replace("{", "{{").replace("}", "}}")
    prompt = ChatPromptTemplate.from_messages([
        ("system", safe_system + "\n\nContext:\n{context}"),
        ("human", "{question}"),
    ])
    return prompt | llm | StrOutputParser()


def answer_question(chain, question, show_context=False):
    """Lab 12: search the knowledge base, then ask the AI to answer from what was found."""
    found = get_retriever().invoke(question)
    context = format_docs(found)
    if show_context:
        print("----- CONTEXT SENT TO THE AI -----")
        print(context)
        print("----------------------------------")
    answer = chain.invoke({"context": context, "question": question})
    sources = sorted({doc.metadata["source"] for doc in found})
    print("QUESTION:", question)
    print("ANSWER:  ", answer)
    print("SOURCES: ", ", ".join(sources))
    print()
    return answer


if __name__ == "__main__":
    from assistant import build_llm
    chain = build_rag_chain(build_llm())
    answer_question(chain, " ".join(sys.argv[1:]) or "ما هي فوائد التغذية الصحية", show_context=True)
