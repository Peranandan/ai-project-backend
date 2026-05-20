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

API_KEY = os.getenv("ANTHROPIC_API_KEY")
API_URL = "https://api.anthropic.com/v1/messages"

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
        headers = {
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        body = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 450,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": request.message}
            ]
        }

        response = requests.post(API_URL, headers=headers, json=body)
        data = response.json()

        if response.status_code == 200:
            text = data["content"][0]["text"]
            return {"success": True, "response": text}

        elif response.status_code == 401:
            return {"success": False, "detail": "Invalid API key. Check your .env file."}

        elif response.status_code == 429:
            return {"success": False, "detail": "Rate limit reached. Try again shortly."}

        elif response.status_code == 500:
            return {"success": False, "detail": "Anthropic server error. Try again."}

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