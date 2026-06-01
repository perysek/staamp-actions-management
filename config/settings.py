import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Pervasive DB DSN (Windows ODBC — configured on the server)
PERVASIVE_DSN = os.environ.get("PERVASIVE_DSN", "STAAMP_DB")

# SQLite database path
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "database.db"))

# Use mock data when Pervasive DB is unavailable (development)
USE_MOCK_DB = os.environ.get("USE_MOCK_DB", "false").lower() == "true"
