import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import bcrypt
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

print(f"Connecting to {DB_URL}")
engine = create_engine(DB_URL)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    gender = Column(String(20))
    dob = Column(DateTime)
    profile_image = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

print("Creating tables...")
Base.metadata.create_all(engine)
print("Tables created!")
