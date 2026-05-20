from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
async def chat(request: ChatRequest):
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=450,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": request.message}
            ]
        )

        response_text = message.content[0].text

        return {
            "success": True,
            "response": response_text
        }

    except anthropic.AuthenticationError:
        return {
            "success": False,
            "detail": "Invalid API key. Please check your ANTHROPIC_API_KEY in .env file."
        }

    except anthropic.RateLimitError:
        return {
            "success": False,
            "detail": "Rate limit reached. Please wait a moment and try again."
        }

    except anthropic.APIConnectionError:
        return {
            "success": False,
            "detail": "Cannot connect to Anthropic API. Check your internet connection."
        }

    except Exception as e:
        return {
            "success": False,
            "detail": str(e)
        }


@app.get("/")
def root():
    return {"status": "AI Project Generator API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}