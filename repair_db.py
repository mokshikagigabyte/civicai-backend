import os
import sys
from sqlalchemy import create_engine, text
from database import Base
from config import DB_URL, DB_CONFIG

def repair():
    print(f"🛠️  Repairing Database: {DB_CONFIG['database']}...")
    
    # Create engine with isolation_level='AUTOCOMMIT' for administrative tasks
    # We first connect to 'postgres' database to drop the 'legal_app_db' if needed,
    # OR we just drop tables inside the 'legal_app_db'. 
    # Let's drop tables inside the 'legal_app_db'.
    
    engine = create_engine(DB_URL)
    
    try:
        with engine.connect() as conn:
            conn.execute(text("COMMIT")) # Ensure we are not in a transaction
            
            # Kill other connections to this database (to avoid 'object in use' error)
            print("👤 Terminating active session to allow schema reset...")
            kill_query = text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DB_CONFIG['database']}'
                  AND pid <> pg_backend_pid();
            """)
            conn.execute(kill_query)
            conn.execute(text("COMMIT"))
            
        # Now drop and create
        print("🗑️  Dropping outdated tables...")
        Base.metadata.drop_all(engine)
        
        print("🏗️  Recreating tables with new schema (Username, Gender, DOB)...")
        Base.metadata.create_all(engine)
        
        print("✅ Database Repair Complete!")
        
    except Exception as e:
        print(f"❌ Repair Failed: {e}")
        print("\nTIP: Please close pgAdmin or any other database tools and try again.")
        sys.exit(1)

if __name__ == "__main__":
    repair()
