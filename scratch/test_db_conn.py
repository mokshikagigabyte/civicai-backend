from sqlalchemy import create_engine, text
from config import DB_URL
import time

def test_conn():
    print(f"Testing connection to {DB_URL.split('@')[-1]}")
    try:
        engine = create_engine(DB_URL, connect_args={'connect_timeout': 5})
        start = time.time()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Success! Result: {result.fetchone()}")
            print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_conn()
