import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# ----------------------------
# Configure Gemini
# ----------------------------
genai.configure(api_key=API_KEY)

# ⚠️ Gemini 2.5 Flash Lite model
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(
    title="Gemini 2.5 Flash Lite API",
    description="FastAPI backend using Google Gemini 2.5 Flash Lite",
    version="1.0.0"
)

# ----------------------------
# CORS (important for Vercel / frontend)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Request schema
# ----------------------------
class ChatRequest(BaseModel):
    message: str

# ----------------------------
# Health check route
# ----------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "model": "gemini-2.5-flash-lite"
    }

# ----------------------------
# Chat endpoint
# ----------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        response = model.generate_content(req.message)

        return {
            "success": True,
            "input": req.message,
            "response": response.text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ----------------------------
# Optional: streaming endpoint (basic simulation)
# ----------------------------
@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    try:
        response = model.generate_content(req.message, stream=True)

        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text

        return {
            "success": True,
            "response": full_text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))