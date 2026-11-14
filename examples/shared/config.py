import os
from pathlib import Path

from dotenv import load_dotenv

EXAMPLES_DIR = Path(__file__).resolve().parents[1]
load_dotenv(EXAMPLES_DIR / ".env")
API_URL = os.getenv("TEMPR_API_URL", "http://localhost:8080/api/v1").rstrip("/")
CASE_COUNT = 5
