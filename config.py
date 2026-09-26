"""
Maple Quiz Buddy V2 - Global Configuration
Loads all keys from .env with fallback defaults to prevent crashes.
"""
from dotenv import load_dotenv
import os

load_dotenv()

# ----- API Keys -----
XAI_API_KEY = os.getenv("XAI_API_KEY", "TEST_XAI_API_KEY_123456")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4")

# ----- LangFuse -----
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# ----- Gmail SMTP -----
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")

# ----- Path Configuration -----
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_PATH = os.path.join(DATA_DIR, "discover_canada.pdf")
VECTOR_STORE_PATH = os.path.join(DATA_DIR, "vectorstore")
SCORE_LOG_PATH = os.path.join(DATA_DIR, "score_log.json")
WRONG_ANSWERS_PATH = os.path.join(DATA_DIR, "wrong_answers.json")

# ----- Quiz Configuration -----
QUESTIONS_PER_QUIZ = 20
PASSING_SCORE = 0.75
MAX_ATTEMPTS = 5

# ----- Sandbox Mode -----
SANDBOX_MODE = XAI_API_KEY.startswith("TEST_")

def is_sandbox():
    """Returns True when using mock keys -- tool modules should return mock data."""
    return SANDBOX_MODE
