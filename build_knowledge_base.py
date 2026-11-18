"""Build the knowledge base: our Lab 10 + Lab 11 code, as one script.

Run:  python build_knowledge_base.py

Step 1  Download the web pages in knowledge/web_sources.json with Beautiful Soup   (Lab 10)
        and read any .txt / .pdf files we put in knowledge/ by hand              (Lab 11 loaders)
Step 2  Clean the text with our Arabic clean_text()                              (Lab 10)
Step 3  Split into chunks of MAX_CHARS, keeping the source file name             (Lab 10)
Step 4  Merge short headings like "السعرات الحرارية:" into the next chunk         (Lab 11)
Step 5  Save knowledge_base.json                                                 (Lab 10)
Step 6  Embeddings (multilingual model) -> vector_store.json                     (Lab 11)
Step 7  Test the search with our Lab 11 questions                                (Lab 11)
"""
import json
import re

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore

from rag import get_embeddings
from settings import CONFIG, KNOWLEDGE_BASE_JSON, KNOWLEDGE_DIR, VECTOR_STORE_JSON, WEB_SOURCES

MAX_CHARS = CONFIG["max_chars"]
MIN_CHUNK_CHARS = CONFIG["min_chunk_chars"]


# ---------- Step 1: collect documents ----------
def download_page(url: str) -> str:
    """Lab 10: download a page and keep its text."""
    response = requests.get(url, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def load_documents() -> dict[str, str]:
    """One document per file name, like DOCUMENTS in Lab 10."""
    documents = {}
    if WEB_SOURCES.exists():
        for item in json.loads(WEB_SOURCES.read_text(encoding="utf-8")):
            saved = KNOWLEDGE_DIR / item["file"]
            if not saved.exists():  # download once, then keep a copy in knowledge/
                try:
                    saved.write_text(download_page(item["url"]), encoding="utf-8")
                    print(f"  downloaded {item['file']}")
                except Exception as error:
                    print(f"  FAILED {item['url']}: {error}")
                    continue
    for path in sorted(KNOWLEDGE_DIR.iterdir()):
        if path.suffix == ".txt":
            documents[path.name] = path.read_text(encoding="utf-8")
        elif path.suffix == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader  # Lab 11
            documents[path.name] = "\n".join(p.page_content for p in PyPDFLoader(str(path)).load())
    return documents


# ---------- Step 2: clean (our Lab 10 function) ----------
REMOVE_HTML = True
REMOVE_WEBSITE_TEXT = True
FIX_SYMBOLS = True
FIX_SPACES = True
REMOVE_REPEATS = True


def clean_text(text):
    """Clean the Arabic nutrition article."""

    # 1. Remove HTML tags if the document contains them.
    if REMOVE_HTML:
        text = re.sub(r"<[^>]+>", " ", text)

    # 2. Remove invisible characters copied from the webpage.
    # Includes zero-width spaces, direction marks, and the BOM.
    text = re.sub(r"[​-‏‪-‮⁦-⁩﻿]", "", text)

    # Normalize Windows and older Mac line endings.
    text = re.sub(r"\r\n?", "\n", text)

    # 3. Keep the article between "مقدمة:" and the website footer (MOH pages).
    if REMOVE_WEBSITE_TEXT:
        start = re.search(r"(?m)^[ \t]*مقدمة[ \t]*[:：]", text)

        if start:
            text = text[start.start():]

        # Matches "في هذا القسم" even when split across lines.
        text = re.split(
            r"(?m)^[ \t]*في[ \t]+هذا\s+القسم[ \t]*(?=\n|$)",
            text,
            maxsplit=1
        )[0]

    # 4. Reduce repeated punctuation.
    if FIX_SYMBOLS:
        text = re.sub(r"([؟?!！.،,؛;])\1+", r"\1", text)

    result = []
    seen = set()

    for line in text.splitlines():

        # 5. Normalize spaces without removing paragraph boundaries.
        if FIX_SPACES:
            line = re.sub(r"[^\S\n]+", " ", line).strip()

            # Remove spaces before punctuation.
            line = re.sub(r"\s+([،؛:.!؟?٪%])", r"\1", line)

            # Remove spaces just inside parentheses.
            line = re.sub(r"\(\s+", "(", line)
            line = re.sub(r"\s+\)", ")", line)

        # 6. Remove duplicate lines.
        if REMOVE_REPEATS and line:
            if line in seen:
                continue
            seen.add(line)

        result.append(line)

    # 7. Keep at most one blank line between paragraphs.
    return re.sub(r"\n{3,}", "\n\n", "\n".join(result)).strip()


# ---------- Step 3: chunk (our Lab 10 function) ----------
def split_into_chunks(text, max_chars):
    """Split text into chunks. Paragraphs stay together, up to max_chars."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = (current + "\n\n" + paragraph) if current else paragraph
    if current:
        chunks.append(current)
    return chunks


# ---------- Step 4: merge short headings (our Lab 11 fix) ----------
def merge_short_chunks(chunks):
    """Merge short headings with the following chunk of the same file."""
    new_chunks, i = [], 0
    while i < len(chunks):
        chunk = chunks[i].copy()
        if (len(chunk["text"].strip()) < MIN_CHUNK_CHARS and i + 1 < len(chunks)
                and chunks[i + 1]["source"] == chunk["source"]):
            chunk["text"] += "\n" + chunks[i + 1]["text"]
            i += 1
        new_chunks.append(chunk)
        i += 1
    for index, chunk in enumerate(new_chunks, start=1):
        chunk["id"] = index
    return new_chunks


def main():
    print("Step 1: documents")
    documents = load_documents()
    if not documents:
        raise SystemExit("No documents. Check knowledge/web_sources.json or add .txt files to knowledge/.")

    print("Step 2+3: clean and chunk")
    knowledge_base = []
    for name, text in documents.items():
        for piece in split_into_chunks(clean_text(text), MAX_CHARS):
            knowledge_base.append({"id": len(knowledge_base) + 1, "source": name, "text": piece})
    print("  chunks:", len(knowledge_base))

    print("Step 4: merge short headings")
    knowledge_base = merge_short_chunks(knowledge_base)
    for name in documents:
        print(f"  {name}: {sum(1 for c in knowledge_base if c['source'] == name)} chunks")

    print("Step 5: save knowledge_base.json")
    KNOWLEDGE_BASE_JSON.write_text(json.dumps(knowledge_base, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Step 6: embeddings -> vector_store.json (the first run downloads the model)")
    # The source stays the real file name (e.g. moh_healthy_nutrition.txt), not knowledge_base.json.
    docs = [Document(page_content=c["text"], metadata={"source": c["source"], "id": c["id"]})
            for c in knowledge_base]
    vector_store = InMemoryVectorStore.from_documents(docs, get_embeddings())
    vector_store.dump(str(VECTOR_STORE_JSON))
    print(f"  saved {len(docs)} chunks")

    print("Step 7: test search")
    for question in ["ما هي فوائد التغذية الصحية؟", "كيف أختار الأطعمة الصحية؟", "ما هي عاصمة اليابان؟"]:
        doc, score = vector_store.similarity_search_with_score(question, k=1)[0]
        print(f"  {question} -> [{doc.metadata['source']}] score {score:.2f}: {doc.page_content[:70]!r}")


if __name__ == "__main__":
    main()
