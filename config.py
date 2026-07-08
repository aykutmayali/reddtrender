"""
ReddTrender - Yapılandırma modülü
Çevre değişkenlerinden Reddit API kimlik bilgilerini yükler.
"""

import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False

load_dotenv()

# Reddit API Kimlik Bilgileri
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
USERNAME = os.getenv("REDDIT_USERNAME", "")
PASSWORD = os.getenv("REDDIT_PASSWORD", "")
USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "python:reddtrender:v1.0.0 (by /u/your_username)"
)

# API Ayarları
BASE_URL = "https://oauth.reddit.com"
AUTH_URL = "https://www.reddit.com/api/v1/access_token"

# Varsayılan sorgu parametreleri
DEFAULT_LIMIT = 25
DEFAULT_SUBREDDITS = [
    "worldnews", "technology", "programming", "science",
    "gaming", "movies", "music", "sports", "askreddit"
]
DEFAULT_KEYWORDS = [
    keyword.strip()
    for keyword in os.getenv(
        "REDDTRENDER_KEYWORDS",
        "ai,openai,python,startup,security,privacy,reddit"
    ).split(",")
    if keyword.strip()
]

# Yerel veri ve rapor çıktıları
DATA_DIR = os.getenv("REDDTRENDER_DATA_DIR", "data")
DB_PATH = os.getenv("REDDTRENDER_DB_PATH", os.path.join(DATA_DIR, "reddtrender.db"))
REPORT_DIR = os.getenv("REDDTRENDER_REPORT_DIR", "reports")

# Rate limit yönetimi
RATE_LIMIT_BUFFER = 5  # Kalan istek sayısı bu değerin altına düşerse bekle
