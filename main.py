import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from datetime import datetime

# -------------------------
# APP
# -------------------------
app = FastAPI()

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# GEMINI API KEY
# -------------------------
API_KEY = os.getenv("AIzaSyDL8MqRkUsm8Q6f9noavp4Opp9uwi2Sj2A")

# -------------------------
# CONFIGURE GEMINI 2.5 FLASH LITE
# -------------------------
model = None

if API_KEY:
    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite"
    )

# -------------------------
# DAILY LIMIT SYSTEM
# -------------------------
user_requests = {}
DAILY_LIMIT = 5


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


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {
        "message": "Backend Running 🚀",
        "api_key_loaded": API_KEY is not None,
        "model": "gemini-2.5-flash-lite"
    }


# -------------------------
# GENERATE
# -------------------------
@app.post("/generate")
async def generate(request: Request, data: dict):

    if model is None:
        return {
            "success": False,
            "error": "GEMINI_API_KEY missing in Render environment variables"
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
- Step-by-step implementation
- Code example

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