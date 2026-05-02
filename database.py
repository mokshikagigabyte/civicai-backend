import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session
from datetime import datetime, timezone
import bcrypt
from contextlib import contextmanager
from config import DB_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# --- Global Database Setup ---
engine = create_engine(DB_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(engine)
    logger.info("Database tables initialized successfully!")

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# --- Models ---
# ... (User, ConflictSession, AnalysisResult, AuditLog models stay same) ...

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
    
    sessions = relationship("ConflictSession", back_populates="user")

# ... (rest of models truncated for this chunk) ...
class ConflictSession(Base):
    __tablename__ = 'conflict_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    partyA_statement = Column(Text)
    partyB_statement = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="sessions")
    results = relationship("AnalysisResult", back_populates="session")

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
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

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
    with get_session() as session:
        try:
            new_user = User(
                name=name,
                email=email,
                username=username,
                password_hash=hash_password(password),
                gender=gender,
                dob=dob
            )
            session.add(new_user)
            # Flush immediately so IntegrityErrors are raised HERE (inside the
            # try/except), not later during commit() in get_session().
            session.flush()
            logger.info(f"User created: {email}")
            return True, "User created successfully!"
        except Exception as e:
            session.rollback()
            err_msg = str(e)
            logger.error(f"Registration failed for {email}: {err_msg}")
            # Match against PostgreSQL constraint names (check username FIRST to avoid
            # ambiguity since "email" could appear in username error strings)
            if "users_username_key" in err_msg:
                return False, "This username is already taken. Try another."
            if "users_email_key" in err_msg:
                return False, "This email is already registered. Please login."
            return False, f"Registration failed: {err_msg}"

def authenticate_user(email, password):
    with get_session() as session:
        try:
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
