import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from datetime import datetime

# =====================================
# GLOBALS
# =====================================
model = None
model_error = None
DAILY_LIMIT = 5
user_requests = {}

# =====================================
# API KEY (DO NOT HARD CODE IN PROD)
# =====================================
GEMINI_API_KEY = os.getenv("AIzaSyBO8zuFTURp_fSX72cUqVWUDCeoeYbXVX4")


# =====================================
# STARTUP
# =====================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, model_error

    api_key = (GEMINI_API_KEY or "").strip()

    if not api_key:
        model_error = "Missing GEMINI_API_KEY"
        print("[ERROR]", model_error)
    else:
        try:
            genai.configure(api_key=api_key)

            # ✅ COST OPTIMIZED + WORKING MODEL
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash"
            )

            model_error = None
            print("[STARTUP] Gemini loaded successfully ✅")

        except Exception as e:
            model_error = str(e)
            print("[STARTUP ERROR]", model_error)

    yield


# =====================================
# APP
# =====================================
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================
# RATE LIMIT
# =====================================
def check_limit(ip: str) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")

    if ip not in user_requests:
        user_requests[ip] = {"date": today, "count": 0}

    if user_requests[ip]["date"] != today:
        user_requests[ip] = {"date": today, "count": 0}

    if user_requests[ip]["count"] >= DAILY_LIMIT:
        return False

    user_requests[ip]["count"] += 1
    return True


# =====================================
# ROOT
# =====================================
@app.get("/")
def root():
    return {
        "message": "Backend Running 🚀",
        "model_loaded": model is not None,
        "model_error": model_error
    }


# =====================================
# USAGE
# =====================================
@app.get("/usage")
def usage(request: Request):
    ip = request.client.host
    today = datetime.now().strftime("%Y-%m-%d")

    used = user_requests.get(ip, {}).get("count", 0)

    return {
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used)
    }


# =====================================
# GENERATE
# =====================================
@app.post("/generate")
async def generate(request: Request, data: dict):

    if model is None:
        return {
            "success": False,
            "error": "Model not loaded",
            "details": model_error
        }

    ip = request.client.host

    if not check_limit(ip):
        return {
            "success": False,
            "error": "Daily limit reached"
        }

    department = data.get("department", "")
    technology = data.get("technology", "")
    level = data.get("level", "")

    prompt = f"""
Dept:{department}
Tech:{technology}
Level:{level}

Return:
Title (5 words)
Explanation (1 line)
Features (3 points)
Steps (3 points)
Code (10-15 lines)
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 220
            }
        )

        return {
            "success": True,
            "result": response.text
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }