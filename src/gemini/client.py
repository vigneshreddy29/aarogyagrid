"""Gemini client — plain HTTP, no SDK (avoids the protobuf conflict)."""
import os, requests
from dotenv import load_dotenv

load_dotenv()

# Ordered by preference. Google retires models without warning, so we
# fall through the list rather than depending on any single one.
MODELS = [
    "gemini-3.6-flash",       # Google's recommended current model
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
]

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def get_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    return key


def ask(prompt, system=None, temperature=0.3):
    """Call Gemini, falling through the model list on 404/503."""
    key = get_key()
    if not key:
        return None

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 4000},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    for model in MODELS:
        try:
            r = requests.post(f"{BASE}/{model}:generateContent",
                              params={"key": key}, json=body, timeout=30)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if r.status_code in (404, 503, 429):
                continue          # retired or overloaded — try the next model
            print(f"Gemini {model}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"Gemini {model}: {e}")
    return None

if __name__ == "__main__":
    print(ask("Reply with exactly: CONNECTED"))