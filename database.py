import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Float, event, text as sa_text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import bcrypt
from contextlib import contextmanager
from config import DB_URL, IS_SQLITE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# --- Global Database Setup ---
# Build engine with the correct args for each DB backend
if IS_SQLITE:
    # SQLite doesn't support pool_size, max_overflow, or connect_timeout
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False},  # Required for SQLite with threads
    )
    # Enable WAL mode for better concurrent read performance
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
    logger.info(f"Using SQLite database: {DB_URL}")
else:
    # PostgreSQL – use connection pool and timeout
    # Optimized for cloud deployment (Supabase, RDS, etc.)
    engine = create_engine(
        DB_URL,
        pool_size=5,                 # Reduced slightly for shared DB plans
        max_overflow=10,
        pool_pre_ping=True,          # Detect stale connections before use
        pool_recycle=300,            # Recycle connections every 5 minutes
        connect_args={
            'connect_timeout': 10,
            # Add keepalives to prevent idle connection kills by cloud firewalls
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
    )
    logger.info(f"Using PostgreSQL database: {DB_URL.split('@')[-1]}") # Log only host part for security

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database, creating tables if they don't exist."""
    try:
        # Test connection first
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.warning(f"Database connection test failed: {e}")
        logger.warning("Will attempt to create tables anyway...")

    try:
        # Create all tables defined in models
        Base.metadata.create_all(engine)
        logger.info("Database tables initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In deployment, failing to init tables is critical
        raise

@contextmanager
def get_session():
    """Context manager for database sessions. Handles commits and rollbacks."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session error, rolling back: {e}")
        raise
    finally:
        session.close()

# --- Models ---

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    gender = Column(String(20))
    dob = Column(DateTime)
    profile_image = Column(Text) # Base64 string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    sessions = relationship("ConflictSession", back_populates="user", cascade="all, delete-orphan")

class ConflictSession(Base):
    __tablename__ = 'conflict_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    partyA_statement = Column(Text)
    partyB_statement = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="sessions")
    results = relationship("AnalysisResult", back_populates="session", cascade="all, delete-orphan")

class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('conflict_sessions.id'))
    sentiment_A = Column(String(20))
    toxicity_A = Column(Float)
    violation = Column(Text)
    section = Column(String(100))
    suggestion = Column(Text)
    severity = Column(String(20))
    
    session = relationship("ConflictSession", back_populates="results")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# --- Helper Functions ---

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def user_to_dict(user):
    if not user: return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "username": user.username,
        "gender": user.gender,
        "dob": user.dob.strftime("%Y-%m-%d") if user.dob else None,
        "profile_image": user.profile_image
    }

def create_user(name, email, username, password, gender=None, dob=None):
    """Creates a new user. Handles IntegrityErrors for unique constraints."""
    try:
        with get_session() as session:
            # Check for existing email/username before attempt (cleaner error handling)
            existing_email = session.query(User).filter(User.email.ilike(email.strip().lower())).first()
            if existing_email:
                return False, "This email is already registered. Please login."
            
            existing_user = session.query(User).filter(User.username == username.strip()).first()
            if existing_user:
                return False, "This username is already taken. Try another."

            new_user = User(
                name=name,
                email=email.strip().lower(),
                username=username.strip(),
                password_hash=hash_password(password),
                gender=gender,
                dob=dob
            )
            session.add(new_user)
            session.flush() 
            logger.info(f"User created successfully: {email}")
            return True, "User created successfully!"
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Registration failed for {email}: {err_msg}")
        return False, f"Registration failed: {err_msg}"

def authenticate_user(email, password):
    """Authenticates a user by email and password."""
    try:
        with get_session() as session:
            if not email or not password:
                return None
            
            clean_email = email.strip().lower()
            clean_password = password.strip()
            
            user = session.query(User).filter(User.email.ilike(clean_email)).first()
            
            if user and check_password(clean_password, user.password_hash):
                logger.info(f"User authenticated: {clean_email}")
                return user_to_dict(user)
                
            logger.warning(f"Authentication failed for: {clean_email}")
            return None
    except Exception as e:
        logger.error(f"Auth database error: {e}")
        return None

def reset_password(email, username, new_password):
    """Resets a user's password after verifying email + username match."""
    try:
        with get_session() as session:
            if not email or not username or not new_password:
                return False, "Email, username, and new password are required."

            clean_email = email.strip().lower()
            clean_username = username.strip()

            user = session.query(User).filter(
                User.email.ilike(clean_email),
                User.username == clean_username
            ).first()

            if not user:
                return False, "No account found with this email and username combination."

            user.password_hash = hash_password(new_password)
            session.flush()
            logger.info(f"Password reset successful for: {clean_email}")
            return True, "Password reset successfully!"
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return False, f"Password reset failed: {str(e)}"
