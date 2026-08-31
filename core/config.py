import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "project-925dcd70-fea8-462c-b7a")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("MODEL", "gemini-2.5-flash")
REGION = os.getenv("REGION", "asia-south1")
FIRESTORE_LOCATION = os.getenv("FIRESTORE_LOCATION", "asia-south1")
DEV_BYPASS = os.getenv("DEV_BYPASS", "1") == "1"

DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_HALF_LIFE_DAYS = 7.0

# Gemini Free Tier Rate Throttling
MIN_SECONDS_BETWEEN_CALLS = float(os.getenv("MIN_SECONDS_BETWEEN_CALLS", "3.0"))

OAUTH_CLIENT_SECRET_FILE = os.getenv(
    "OAUTH_CLIENT_SECRET_FILE",
    str(BASE_DIR / "client_secret.json")
)
TOKEN_FILE = os.getenv(
    "TOKEN_FILE",
    str(BASE_DIR / "token.json")
)

OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.send",
]

APP_NAME = "PadhaiKairo"
APP_TAGLINE = "The study coach that works while you sleep."

# Gemini Dual-Mode: API key (dev) vs Vertex AI (prod)
USE_VERTEX_AI = os.getenv("USE_VERTEX_AI", "false").lower() == "true"
VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "asia-south1")
