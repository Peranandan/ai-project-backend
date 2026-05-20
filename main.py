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
# INIT GEMINI LAZY (FIX)
# =====================================
def get_model():
    global model, model_error

    if model is not None:
        return model

    api_key = os.getenv("AIzaSyDUpnD4Yp6E3fYW7qdWnjdhPm99BxVIaho")

    if not api_key:
        model_error = "GEMINI_API_KEY missing in environment"
        return None

    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite"
        )

        model_error = None
        return model

    except Exception as e:
        model_error = str(e)
        return None


# =====================================
# LIMIT
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
    m = get_model()

    return {
        "message": "Backend Running 🚀",
        "api_key_loaded": os.getenv("GEMINI_API_KEY") is not None,
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
            "error": "Daily limit reached"
        }

    prompt = f"""
Domain: {data.get("domain","")}
Technology: {data.get("technology","")}
Level: {data.get("level","")}

Generate:
- Title
- Explanation
- Features
- Steps
- Code
"""

    try:
        response = m.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 300
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