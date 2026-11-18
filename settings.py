"""Settings (Lab 8) and secrets (Day 3).

- What the user sees and the model settings live in config.json, like Lab 8.
- Keys are never written in code. They come from:
  1. environment variables or a .env file (terminal), or
  2. .streamlit/secrets.toml (the Streamlit app, Day 9).
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
WEB_SOURCES = KNOWLEDGE_DIR / "web_sources.json"
KNOWLEDGE_BASE_JSON = BASE_DIR / "knowledge_base.json"  # Lab 10 output
VECTOR_STORE_JSON = BASE_DIR / "vector_store.json"      # Lab 11 output
RESULTS_DIR = BASE_DIR / "results"

with open(BASE_DIR / "config.json", encoding="utf-8") as f:
    CONFIG = json.load(f)


def get_secret(name: str, default=None):
    """Read a key from the environment first, then from Streamlit secrets."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets[name]
    except Exception:
        return default
