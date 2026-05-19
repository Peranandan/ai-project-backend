import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("AIzaSyDL8MqRkUsm8Q6f9noavp4Opp9uwi2Sj2A")

if not API_KEY:
    raise Exception("GEMINI_API_KEY missing")

genai.configure(api_key=API_KEY)

# ⚡ YOUR MODEL (AS REQUESTED)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DAILY LIMIT (6/DAY)
# =========================
user_requests = {}
DAILY_LIMIT = 6


def check_limit(ip: str):
    today = datetime.now().strftime("%Y-%m-%d")

    if ip not in user_requests:
        user_requests[ip] = {"date": today, "count": 0}

    if user_requests[ip]["date"] != today:
        user_requests[ip] = {"date": today, "count": 0}

    if user_requests[ip]["count"] >= DAILY_LIMIT:
        return False

    user_requests[ip]["count"] += 1
    return True


# =========================
# API
# =========================
@app.post("/generate")
async def generate(request: Request, data: dict):

    ip = request.client.host

    if not check_limit(ip):
        raise HTTPException(status_code=429, detail="Daily limit reached (6/day)")

    domain = data.get("domain", "")
    tech = data.get("technology", "")
    level = data.get("level", "")

    # =========================
    # COST OPTIMIZED PROMPT (VERY SHORT)
    # =========================
    prompt = f"""
AI Project Generator

Dept:{domain}
Tech:{tech}
Level:{level}

Give EXACT format:

1.Title
2.Idea
3.Features (3 points)
4.Steps (3-5 points)
5.Code (short example)

Keep response short.
"""

    response = model.generate_content(
        prompt,
        generation_config={
            "max_output_tokens": 450,  # controlled cost
            "temperature": 0.7
        }
    )

    return {
        "success": True,
        "model": "gemini-2.5-flash-lite",
        "limit_remaining": DAILY_LIMIT - user_requests[ip]["count"],
        "result": response.text
    }