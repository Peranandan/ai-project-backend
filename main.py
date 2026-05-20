import os
import hashlib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import google.generativeai as genai

# =========================
# CONFIG
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

DAILY_LIMIT = 5
user_requests = {}

# 🔥 CACHE (KEY FEATURE)
cache = {}

model = None

# =========================
# INIT GEMINI
# =========================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash"
    )

# =========================
# APP
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RATE LIMIT
# =========================
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
# CACHE KEY GENERATOR
# =========================
def generate_cache_key(dept, tech, level):
    raw = f"{dept}-{tech}-{level}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {
        "message": "Backend Running 🚀",
        "model_loaded": model is not None,
        "cache_size": len(cache)
    }

# =========================
# GENERATE (CACHED VERSION)
# =========================
@app.post("/generate")
async def generate(request: Request, data: dict):

    if model is None:
        return {"success": False, "error": "Model not loaded"}

    ip = request.client.host

    if not check_limit(ip):
        return {"success": False, "error": "Daily limit reached"}

    department = data.get("department", "").strip()
    technology = data.get("technology", "").strip()
    level = data.get("level", "").strip()

    if not department or not technology or not level:
        return {"success": False, "error": "Missing fields"}

    # 🔥 CREATE CACHE KEY
    cache_key = generate_cache_key(department, technology, level)

    # =========================
    # RETURN CACHE (NO API CALL)
    # =========================
    if cache_key in cache:
        return {
            "success": True,
            "cached": True,
            "result": cache[cache_key]
        }

    # =========================
    # OPTIMIZED PROMPT
    # =========================
    prompt = f"""
Project idea:

Dept:{department}
Tech:{technology}
Level:{level}

Return:
Title (5 words max)
Explanation (1 line)
Features (3 points)
Implementation (3 steps)
Code (10 lines max)
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 180
            }
        )

        result = response.text

        # 🔥 STORE IN CACHE
        cache[cache_key] = result

        return {
            "success": True,
            "cached": False,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }