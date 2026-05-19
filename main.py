import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("AIzaSyDL8MqRkUsm8Q6f9noavp4Opp9uwi2Sj2A")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
else:
    model = None

# =========================
# APP
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 24-HOUR LIMIT SYSTEM
# =========================
user_requests = {}
DAILY_LIMIT = 6


def check_limit(ip: str):
    now = datetime.utcnow()

    if ip not in user_requests:
        user_requests[ip] = {
            "count": 0,
            "reset_time": now + timedelta(hours=24)
        }

    user_data = user_requests[ip]

    # RESET AFTER 24 HOURS
    if now > user_data["reset_time"]:
        user_data["count"] = 0
        user_data["reset_time"] = now + timedelta(hours=24)

    if user_data["count"] >= DAILY_LIMIT:
        return False, int((user_data["reset_time"] - now).seconds)

    user_data["count"] += 1
    return True, int((user_data["reset_time"] - now).seconds)


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"message": "AI Project Generator Running 🚀"}


# =========================
# GENERATE API
# =========================
@app.post("/generate")
async def generate(request: Request, data: dict):

    if model is None:
        raise HTTPException(status_code=500, detail="Gemini API Key missing")

    ip = request.client.host

    allowed, time_left = check_limit(ip)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached. Try again after {time_left//3600}h {(time_left%3600)//60}m"
        )

    domain = data.get("domain", "")
    tech = data.get("technology", "")
    level = data.get("level", "")

    prompt = f"""
AI Project Generator

Dept:{domain}
Tech:{tech}
Level:{level}

Return:
1.Title
2.Idea
3.Features (3)
4.Steps (3-5)
5.Code (short)
"""

    response = model.generate_content(
        prompt,
        generation_config={
            "max_output_tokens": 400,
            "temperature": 0.7
        }
    )

    return {
        "success": True,
        "result": response.text,
        "remaining": DAILY_LIMIT - user_requests[ip]["count"],
        "reset_in_seconds": time_left
    }