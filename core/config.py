"""Saari settings ek jagah. Apne college ke hisaab se yahin edit karo."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "attendance.db"

BRANCHES = ["CSE", "AI/ML", "ECE", "BCA", "MCA"]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
SECTIONS = ["A", "B", "C", "D"]

# Student registration ke liye photos
MIN_REG_PHOTOS = 3
MAX_REG_PHOTOS = 5

# Chehra match karne ki strictness (chhota = strict). Slider se bhi badal sakte ho.
DEFAULT_TOLERANCE = 0.55

TIMEZONE = "Asia/Kolkata"
