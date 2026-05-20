import os
import hashlib
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")  # ✅ Changed to GEMINI_API_KEY
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# ----------------------------
# Configure Gemini
# ----------------------------
genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash-lite"

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=genai.GenerationConfig(
        max_output_tokens=220,
        temperature=0.7,
        candidate_count=1,
    )
)

# ----------------------------
# Token limits
# ----------------------------
MAX_INPUT_CHARS = 120
MAX_OUTPUT_TOKENS = 220
CACHE_TTL_SECONDS = 300
MAX_HISTORY_TURNS = 10

# ----------------------------
# In-memory cache
# ----------------------------
_cache: dict[str, tuple[str, float]] = {}

def get_cached(prompt: str) -> str | None:
    key = hashlib.md5(prompt.encode()).hexdigest()
    if key in _cache:
        response, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return response
        del _cache[key]
    return None

def set_cache(prompt: str, response: str):
    key = hashlib.md5(prompt.encode()).hexdigest()
    _cache[key] = (response, time.time())
    if len(_cache) > 500:
        oldest = sorted(_cache.items(), key=lambda x: x[1][1])[:100]
        for k, _ in oldest:
            del _cache[k]

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(
    title="Gemini 2.5 Flash-Lite API",
    description="Cost-optimized FastAPI backend using Google Gemini 2.5 Flash-Lite",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Schemas
# ----------------------------
class ChatRequest(BaseModel):
    message: str
    use_cache: bool = True

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > MAX_INPUT_CHARS:
            raise ValueError(f"Message too long (max {MAX_INPUT_CHARS} characters)")
        return v


class Message(BaseModel):
    role: str
    text: str


class MultiTurnRequest(BaseModel):
    history: list[Message] = []
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > MAX_INPUT_CHARS:
            raise ValueError(f"Message too long (max {MAX_INPUT_CHARS} characters)")
        return v

    @field_validator("history")
    @classmethod
    def validate_history(cls, v):
        return v[-MAX_HISTORY_TURNS:] if len(v) > MAX_HISTORY_TURNS else v


# ----------------------------
# Health check
# ----------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "model": MODEL_NAME,
        "max_input_chars": MAX_INPUT_CHARS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "cache_size": len(_cache)
    }


# ----------------------------
# Single-turn chat (with cache)
# ----------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    if req.use_cache:
        cached = get_cached(req.message)
        if cached:
            return {
                "success": True,
                "input": req.message,
                "response": cached,
                "cached": True
            }

    try:
        response = model.generate_content(
            req.message,
            generation_config=genai.GenerationConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                candidate_count=1,
            )
        )
        text = response.text

        if req.use_cache:
            set_cache(req.message, text)

        return {
            "success": True,
            "input": req.message,
            "response": text,
            "cached": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")


# ----------------------------
# Streaming chat
# ----------------------------
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    def generate():
        try:
            response = model.generate_content(
                req.message,
                stream=True,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    candidate_count=1,
                )
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"[ERROR]: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


# ----------------------------
# Multi-turn chat
# ----------------------------
@app.post("/chat/multi")
async def chat_multi(req: MultiTurnRequest):
    try:
        history = [
            {"role": msg.role, "parts": [msg.text]}
            for msg in req.history
            if msg.role in ("user", "model")
        ]

        chat_session = model.start_chat(history=history)
        response = chat_session.send_message(
            req.message,
            generation_config=genai.GenerationConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                candidate_count=1,
            )
        )

        return {
            "success": True,
            "input": req.message,
            "response": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")