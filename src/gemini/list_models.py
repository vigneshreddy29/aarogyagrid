import os, requests
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("GEMINI_API_KEY")
r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                 params={"key": key}, timeout=20)

if r.status_code != 200:
    print("ERROR", r.status_code, r.text[:400])
else:
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"])