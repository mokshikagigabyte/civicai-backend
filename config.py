import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()

def get_db_url():
    """
    Constructs or retrieves the database URL, ensuring it's compatible with SQLAlchemy.
    Priority: DATABASE_URL env var > constructed from DB_HOST/DB_PORT/etc > SQLite fallback
    """
    db_url = os.getenv("DATABASE_URL", "")
    
    # 1. Build the URL from components only if DATABASE_URL is NOT provided
    if not db_url:
        db_host = os.getenv("DB_HOST", "")
        db_user = os.getenv("DB_USER", "")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "postgres")

        if db_host and db_user:
            safe_password = quote_plus(db_pass)
            db_url = f"postgresql://{db_user}:{safe_password}@{db_host}:{db_port}/{db_name}"
    
    # 2. Fix 'postgres://' prefix which is common in older deployment platforms (like Heroku/Render)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # 3. Add SSL mode if it's a remote PostgreSQL database and not already present
    if "postgresql" in db_url and "localhost" not in db_url and "127.0.0.1" not in db_url:
        if "sslmode" not in db_url:
            separator = "&" if "?" in db_url else "?"
            # Note: For some platforms like Supabase, sslmode=require is essential
            db_url += f"{separator}sslmode=require"

    # 4. Fallback to SQLite if nothing else is configured
    if not db_url:
        db_url = "sqlite:///./test.db"
        
    return db_url

# Final configuration values
DB_URL = get_db_url()
IS_SQLITE = DB_URL.startswith("sqlite")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
