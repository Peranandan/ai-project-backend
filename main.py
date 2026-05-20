from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """You are an engineering project generator. Be concise and practical.

Respond with EXACTLY these sections, no extras:

Project Title: <title>

Explanation:
<2 sentences about what the project does>

Features:
- <feature 1>
- <feature 2>
- <feature 3>
- <feature 4>

Architecture Overview:
<1-2 sentences on system structure>

Components:
<1 sentence listing main components>

Steps:
- Step 1: <action>
- Step 2: <action>
- Step 3: <action>
- Step 4: <action>
- Step 5: <action>

Code:
```python
# concise working code, max 30 lines
```

Code Explanation:
<2 sentences explaining the code and how to run it>

Keep total response under 400 tokens. Be direct, no filler words."""


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        if not GEMINI_API_KEY:
            return {"success": False, "detail": "GEMINI_API_KEY not set in .env file"}

        headers = {
            "Content-Type": "application/json"
        }

        body = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": request.message}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 450,
                "temperature": 0.7
            }
        }

        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=body,
            timeout=30
        )

        data = response.json()

        if response.status_code == 200:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "response": text}

        elif response.status_code == 400:
            return {"success": False, "detail": "Bad request. Check your input."}

        elif response.status_code == 403:
            return {"success": False, "detail": "Invalid API key. Check your GEMINI_API_KEY in .env file."}

        elif response.status_code == 429:
            return {"success": False, "detail": "Rate limit reached. Please wait and try again."}

        elif response.status_code == 500:
            return {"success": False, "detail": "Gemini server error. Try again."}

        else:
            return {"success": False, "detail": f"API error {response.status_code}: {data}"}

    except requests.exceptions.ConnectionError:
        return {"success": False, "detail": "No internet connection."}

    except requests.exceptions.Timeout:
        return {"success": False, "detail": "Request timed out. Try again."}

    except Exception as e:
        return {"success": False, "detail": str(e)}


@app.get("/")
def root():
    return {"status": "AI Project Generator API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}