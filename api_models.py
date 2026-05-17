from pydantic import BaseModel, Field
from typing import List, Optional
from conflic_model.schemas import ConflictReport

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    username: str
    password: str
    gender: Optional[str] = None
    dob: Optional[str] = None # Expecting ISO format or YYYY-MM-DD

class ResetPasswordRequest(BaseModel):
    email: str
    username: str
    new_password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    enable_web: bool = True
    model_name: str = "llama-3.3-70b-versatile"

class SearchResponse(BaseModel):
    answer: str
    sources: List[str]

class ConflictAnalysisRequest(BaseModel):
    party_a: str
    party_b: str
