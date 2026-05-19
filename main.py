import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai

# =========================
# LOAD ENV FILE
# =========================
load_dotenv()

API_KEY = os.getenv("AIzaSyDL8MqRkUsm8Q6f9noavp4Opp9uwi2Sj2A")

# =========================
# GEMINI CONFIG
# =========================
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# =========================
# FASTAPI APP
# =========================
app = FastAPI()

# =========================
# CORS SETUP (IMPORTANT)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HOME ROUTE
# =========================
@app.get("/")
def home():
    return {"message": "AI Project Generator API Running"}

# =========================
# GENERATE PROJECT API
# =========================
@app.post("/generate")
async def generate(data: dict):

    try:
        domain = data.get("domain", "")
        technology = data.get("technology", "")
        level = data.get("level", "")

        # 🚀 COST-OPTIMIZED PROMPT (SHORT = CHEAPER)
        prompt = f"""
Create AI Project:

Department: {domain}
Technology: {technology}
Level: {level}

Return:
Title
Overview
Steps
Code (short)
"""

        response = model.generate_content(prompt)

        return {
            "success": True,
            "result": response.text
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }