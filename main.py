import os
import hashlib

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import google.generativeai as genai

# =========================
# ENV CONFIG
# =========================
GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

# =========================
# GLOBALS
# =========================
model = None

user_requests = {}

cache = {}

DAILY_LIMIT = 5

# =========================
# INIT GEMINI
# =========================
if GEMINI_API_KEY:

    genai.configure(
        api_key=GEMINI_API_KEY
    )

    # ✅ WORKING MODEL
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash"
    )

    print(
        "Gemini Loaded Successfully"
    )

else:

    print(
        "GEMINI_API_KEY not found"
    )

# =========================
# FASTAPI APP
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
# RATE LIMIT
# =========================
def check_limit(ip):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if ip not in user_requests:

        user_requests[ip] = {
            "date": today,
            "count": 0
        }

    if (
        user_requests[ip]["date"]
        != today
    ):

        user_requests[ip] = {
            "date": today,
            "count": 0
        }

    if (
        user_requests[ip]["count"]
        >= DAILY_LIMIT
    ):

        return False

    user_requests[ip]["count"] += 1

    return True

# =========================
# CACHE KEY
# =========================
def get_cache_key(
    dept,
    tech,
    level
):

    raw = (
        f"{dept}-{tech}-{level}"
    ).lower().strip()

    return hashlib.md5(
        raw.encode()
    ).hexdigest()

# =========================
# ROOT
# =========================
@app.get("/")
def root():

    return {

        "message":
        "Backend Running 🚀",

        "model_loaded":
        model is not None,

        "cache_size":
        len(cache)
    }

# =========================
# GENERATE
# =========================
@app.post("/generate")
async def generate(
    request: Request,
    data: dict
):

    # =====================
    # MODEL CHECK
    # =====================
    if model is None:

        return {

            "success": False,

            "error":
            "Gemini model not loaded"
        }

    # =====================
    # USER IP
    # =====================
    ip = request.client.host

    # =====================
    # LIMIT CHECK
    # =====================
    if not check_limit(ip):

        return {

            "success": False,

            "error":
            "Daily limit reached"
        }

    # =====================
    # INPUTS
    # =====================
    department = data.get(
        "department",
        ""
    ).strip()

    technology = data.get(
        "technology",
        ""
    ).strip()

    level = data.get(
        "level",
        ""
    ).strip()

    # =====================
    # VALIDATION
    # =====================
    if (
        not department or
        not technology or
        not level
    ):

        return {

            "success": False,

            "error":
            "Missing fields"
        }

    # =====================
    # CACHE KEY
    # =====================
    cache_key = get_cache_key(
        department,
        technology,
        level
    )

    # =====================
    # RETURN CACHE
    # =====================
    if cache_key in cache:

        return {

            "success": True,

            "cached": True,

            "result":
            cache[cache_key]
        }

    # =====================
    # PROMPT
    # =====================
    prompt = f"""
Generate a project idea.

Department:
{department}

Technology:
{technology}

Difficulty:
{level}

Return format:

Title:
(5 words max)

Explanation:
(1 line)

Features:
(3 bullet points)

Implementation:
(3 steps)

Code:
(10 lines max)
"""

    # =====================
    # GEMINI REQUEST
    # =====================
    try:

        response = model.generate_content(

            prompt,

            generation_config={

                "temperature": 0.2,

                "max_output_tokens": 180
            }
        )

        result = response.text

        # =================
        # SAVE CACHE
        # =================
        cache[cache_key] = result

        return {

            "success": True,

            "cached": False,

            "result": result
        }

    # =====================
    # ERROR
    # =====================
    except Exception as e:

        return {

            "success": False,

            "error": str(e)
        }