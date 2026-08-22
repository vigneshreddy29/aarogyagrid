import os, requests
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("GEMINI_API_KEY")

for model in ["gemini-2.5-flash", "gemini-flash-latest"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(url, params={"key": key},
                      json={"contents": [{"parts": [{"text": "Say CONNECTED"}]}]},
                      timeout=25)
    print(f"\n--- {model} -> {r.status_code}")
    if r.status_code == 200:
        print(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    else:
        print(r.text[:500])