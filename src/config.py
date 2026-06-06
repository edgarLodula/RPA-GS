import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "asteroides.db"
NASA_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"

nasa_api = os.getenv("NASA_API_KEY")

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
