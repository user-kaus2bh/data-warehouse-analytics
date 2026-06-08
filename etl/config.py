"""
config.py — Central configuration loader for the ETL pipeline.
Reads from .env file and exposes typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ─── Paths ────────────────────────────────────────────────────────────────────
RAW_DATA_DIR      = BASE_DIR / os.getenv("RAW_DATA_DIR", "data/raw")
PROCESSED_DATA_DIR = BASE_DIR / os.getenv("PROCESSED_DATA_DIR", "data/processed")
LOG_DIR           = BASE_DIR / os.getenv("LOG_DIR", "logs")
DB_PATH           = BASE_DIR / os.getenv("DB_PATH", "data/warehouse.db")

# ─── Database ─────────────────────────────────────────────────────────────────
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "postgresql":
    DB_URL = (
        f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
        f"@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
    )
else:
    DB_URL = f"sqlite:///{DB_PATH}"

# ─── Data Generation ──────────────────────────────────────────────────────────
NUM_CUSTOMERS = int(os.getenv("NUM_CUSTOMERS", 500))
NUM_PRODUCTS  = int(os.getenv("NUM_PRODUCTS", 50))
NUM_ORDERS    = int(os.getenv("NUM_ORDERS", 5000))
NUM_CAMPAIGNS = int(os.getenv("NUM_CAMPAIGNS", 20))
START_DATE    = os.getenv("START_DATE", "2022-01-01")
END_DATE      = os.getenv("END_DATE", "2024-12-31")

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Ensure directories exist ─────────────────────────────────────────────────
for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, LOG_DIR, DB_PATH.parent]:
    d.mkdir(parents=True, exist_ok=True)
