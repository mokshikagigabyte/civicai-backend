import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration – reads from .env or falls back to defaults
DB_CONFIG = {
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "legal_app_db")
}

# Connection string template
DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
