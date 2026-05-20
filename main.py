import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from datetime import datetime

# =====================================
# APP
# =====================================
app = FastAPI(title="AI Project Generator")

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
# GLOBALS
# =====================================
model = None
model_error = None

DAILY_LIMIT = 5
user_requests = {}

# =====================================
# INIT GEMINI (SAFE RUNTIME LOAD)
# =====================================
def init_gemini():
    global model, model_error

    api_key = os.getenv("AIzaSyDUpnD4Yp6E3fYW7qdWnjdhPm99BxVIaho")

    if not api_key:
        model_error = "GEMINI_API_KEY not found in environment"
        model = None
        return

    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite"
        )

        model_error = None

    except Exception as e:
        model = None
        model_error = str(e)


# Run on startup (IMPORTANT FIX)
@app.on_event("startup")
def startup_event():
    init_gemini()


# =====================================
# LIMIT CHECK
# =====================================
def check_limit(ip):
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
        "api_key_loaded": os.getenv("GEMINI_API_KEY") is not None,
        "model_loaded": model is not None,
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
# GENERATE
# =====================================
@app.post("/generate")
async def generate(request: Request, data: dict):

    if model is None:
        return {
            "success": False,
            "error": "Gemini model not initialized",
            "details": model_error
        }

    ip = request.client.host

    if not check_limit(ip):
        return {
            "success": False,
            "error": "Daily limit reached"
        }

    domain = data.get("domain", "")
    technology = data.get("technology", "")
    level = data.get("level", "")

    prompt = f"""
Domain: {domain}
Technology: {technology}
Level: {level}

Generate:
- Project Title
- Explanation
- Features
- Steps
- Code

Keep it short and structured.
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 300
            }
        )

        return {
            "success": True,
            "result": response.text,
            "remaining_requests": DAILY_LIMIT - user_requests[ip]["count"]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }