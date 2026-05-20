import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import google.generativeai as genai

from datetime import datetime

# =====================================
# FASTAPI APP
# =====================================
app = FastAPI()

# =====================================
# CORS
# =====================================
app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# =====================================
# GEMINI API KEY
# =====================================
API_KEY = os.getenv("AIzaSyDL8MqRkUsm8Q6f9noavp4Opp9uwi2Sj2A")

# =====================================
# CONFIGURE GEMINI
# =====================================
model = None

if API_KEY:

    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel(
        "gemini-2.5-flash-lite"
    )

# =====================================
# DAILY LIMIT
# =====================================
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


# =====================================
# ROOT ROUTE
# =====================================
@app.get("/")
async def root():

    return {
        "message": "Backend Running 🚀",
        "api_key_loaded": API_KEY is not None
    }


# =====================================
# GENERATE ROUTE
# =====================================
@app.post("/generate")
async def generate(request: Request, data: dict):

    # CHECK API KEY
    if model is None:

        return {
            "success": False,
            "error": "GEMINI_API_KEY missing in Render"
        }

    ip = request.client.host

    # DAILY LIMIT
    if not check_limit(ip):

        return {
            "success": False,
            "error": "Daily limit reached. Try again after 24 hours."
        }

    # INPUTS
    domain = data.get("domain", "")
    technology = data.get("technology", "")
    level = data.get("level", "")

    # =====================================
    # LOW COST PROMPT
    # =====================================
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

        # GEMINI RESPONSE
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

        return {

            "success": False,

            "error": str(e)
        }