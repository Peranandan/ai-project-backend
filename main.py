import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import google.generativeai as genai

from datetime import datetime

# =========================
# GET GEMINI API KEY
# =========================
API_KEY = os.getenv("GEMINI_API_KEY")

# CHECK KEY
if API_KEY is None or API_KEY == "":
    raise Exception(
        "GEMINI_API_KEY missing in Render Environment Variables"
    )

# CONFIGURE GEMINI
genai.configure(api_key=API_KEY)

# MODEL
model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# =========================
# FASTAPI
# =========================
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
# DAILY LIMIT
# =========================
user_requests = {}

DAILY_LIMIT = 5


def check_limit(ip):

    today = datetime.now().strftime("%Y-%m-%d")

    # NEW USER
    if ip not in user_requests:

        user_requests[ip] = {
            "date": today,
            "count": 0
        }

    # RESET DAILY
    if user_requests[ip]["date"] != today:

        user_requests[ip] = {
            "date": today,
            "count": 0
        }

    # LIMIT REACHED
    if user_requests[ip]["count"] >= DAILY_LIMIT:
        return False

    # INCREMENT
    user_requests[ip]["count"] += 1

    return True


# =========================
# ROOT
# =========================
@app.get("/")
async def root():

    return {
        "message": "AI Project Generator Running 🚀"
    }


# =========================
# GENERATE
# =========================
@app.post("/generate")
async def generate(request: Request, data: dict):

    ip = request.client.host

    # CHECK LIMIT
    if not check_limit(ip):

        raise HTTPException(
            status_code=429,
            detail="Daily limit reached. Resets after 24 hours."
        )

    # INPUTS
    domain = data.get("domain", "")
    technology = data.get("technology", "")
    level = data.get("level", "")

    # =========================
    # LOW COST PROMPT
    # =========================
    prompt = f"""
Dept:{domain}
Tech:{technology}
Level:{level}

Format:
Title:
Explanation:
Features:
Implementation:
Code:

Short concise response only.
"""

    try:

        response = model.generate_content(
            prompt,

            generation_config={
                "max_output_tokens": 220,
                "temperature": 0.4
            }
        )

        return {
            "success": True,

            "remaining_requests":
                DAILY_LIMIT - user_requests[ip]["count"],

            "result": response.text
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )