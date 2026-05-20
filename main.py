import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
model_error = None

DAILY_LIMIT = 5
user_requests = {}


# =====================================
# INIT GEMINI LAZY
# =====================================
def get_model():
    global model, model_error

    if model is not None:
        return model

    # ✅ FIXED: was os.getenv("") before
    api_key = os.getenv("AIzaSyDUpnD4Yp6E3fYW7qdWnjdhPm99BxVIaho")

    if not api_key:
        model_error = "GEMINI_API_KEY missing in environment"
        return None

    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash"
        )

        model_error = None
        return model

    except Exception as e:
        model_error = str(e)
        return None


# =====================================
# LIMIT
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
    m = get_model()
    return {
        "message": "Backend Running 🚀",
        "api_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
        "model_loaded": m is not None,
        "model_error": model_error
    }


# =====================================
# DEBUG
# =====================================
@app.get("/env-check")
def env_check():
    return {
        "GEMINI_API_KEY_in_env": "GEMINI_API_KEY" in os.environ,
        "GEMINI_API_KEY_loaded": bool(os.getenv("GEMINI_API_KEY")),
        "model_loaded": model is not None,
        "model_error": model_error
    }


# =====================================
# USAGE INFO
# =====================================
@app.get("/usage")
def usage(request: Request):
    ip = request.client.host
    today = datetime.now().strftime("%Y-%m-%d")

    if ip not in user_requests or user_requests[ip]["date"] != today:
        used = 0
    else:
        used = user_requests[ip]["count"]

    return {
        "ip": ip,
        "used": used,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - used)
    }


# =====================================
# GENERATE
# =====================================
@app.post("/generate")
async def generate(request: Request, data: dict):
    m = get_model()

    if m is None:
        return {
            "success": False,
            "error": "Gemini model not initialized",
            "details": model_error
        }

    ip = request.client.host

    if not check_limit(ip):
        return {
            "success": False,
            "error": f"Daily limit of {DAILY_LIMIT} requests reached. Try again tomorrow."
        }

    domain     = data.get("domain", "").strip()
    technology = data.get("technology", "").strip()
    level      = data.get("level", "").strip()

    if not domain or not technology or not level:
        return {
            "success": False,
            "error": "domain, technology, and level are all required."
        }

    prompt = f"""
You are a technical mentor. Generate a structured learning resource.

Domain: {domain}
Technology: {technology}
Level: {level}

Respond with:
- Title
- Explanation (2-3 sentences)
- Key Features (3-5 bullet points)
- Steps to Get Started (numbered list)
- Sample Code (with comments)
"""

    try:
        response = m.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 800
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