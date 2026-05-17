from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uvicorn
import json
import os
import sys
from datetime import datetime, timezone
import traceback
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio

from database import authenticate_user, create_user, reset_password, init_db, get_session
from api_models import (
    LoginRequest, RegisterRequest, ResetPasswordRequest, AuthResponse, 
    SearchRequest, SearchResponse, ConflictReport
)
from config import GROQ_API_KEY

# import faiss, pickle, and ConflictProcessor removed for lazy loading
from groq import AsyncGroq
from duckduckgo_search import DDGS

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and load AI models on startup."""
    logger.info("🚀 Starting up CivicAI API...")
    try:
        # Initialize Database tables with retry
        for attempt in range(3):
            try:
                init_db()
                logger.info("✅ Database initialized.")
                break
            except Exception as db_e:
                logger.warning(f"⚠️ DB init attempt {attempt+1}/3 failed: {db_e}")
                if attempt == 2:
                    logger.error("❌ Could not connect to database after 3 attempts. Starting without DB.")
                await asyncio.sleep(2)
        
        # Eagerly load AI resources — increased timeout to 5 minutes
        try:
            await asyncio.wait_for(resources.load_all(), timeout=300.0)
            logger.info("✅ AI Resources (Model, Index, Metadata) loaded successfully.")
        except asyncio.TimeoutError:
            logger.warning("⚠️ AI Resources loading timed out. They will load on first demand.")

    except Exception as e:
        logger.error(f"❌ Startup initialization failed: {e}")
        logger.error(traceback.format_exc())
    
    yield
    logger.info("🛑 Shutting down CivicAI API.")


app = FastAPI(
    title="CivicAI Legal API", 
    version="1.1.0", 
    lifespan=lifespan,
    description="Backend API for Legal AI Assistant and Conflict Monitor"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )

# Enable CORS for Flutter/Web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you should restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- Project root for absolute file paths ---
_ROOT = os.path.dirname(os.path.abspath(__file__))

# Global Resources Singleton
class APIResources:
    def __init__(self):
        self.groq_key = GROQ_API_KEY
        self._index = None
        self._metadata = None
        self._model = None
        self.groq_client = AsyncGroq(api_key=self.groq_key)
        self.processor = None
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def load_all(self):
        """Eagerly load all fast resources (FAISS, Metadata). Load model lazily to allow instant port binding."""
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self._load_index),
            loop.run_in_executor(self.executor, self._load_metadata)
        ]
        await asyncio.gather(*tasks)

    def _load_index(self):
        if self._index is None:
            import faiss
            path = os.path.join(_ROOT, 'motor_vehicles.faiss')
            if os.path.exists(path):
                self._index = faiss.read_index(path)
                logger.info("FAISS index loaded.")
            else:
                logger.error(f"FAISS index file not found at {path}")

    def _load_metadata(self):
        if self._metadata is None:
            import pickle
            path = os.path.join(_ROOT, 'motor_vehicles_metadata.pkl')
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    self._metadata = pickle.load(f)
                logger.info("Metadata loaded.")
            else:
                logger.error(f"Metadata file not found at {path}")

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            # Note: This is memory intensive
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("SentenceTransformer model loaded.")

    @property
    def index(self):
        if self._index is None: self._load_index()
        return self._index

    @property
    def metadata(self):
        if self._metadata is None: self._load_metadata()
        return self._metadata

    @property
    def model(self):
        if self._model is None: self._load_model()
        return self._model

    @property
    def conflict_processor(self):
        if self.processor is None:
            from conflic_model.processor import ConflictProcessor
            self.processor = ConflictProcessor(self.groq_key, self.index, self.metadata, self.model)
        return self.processor

resources = APIResources()

# --- BASE ENDPOINTS ---

@app.get("/")
async def root():
    return {
        "message": "CivicAI Legal API is running",
        "version": "1.1.0",
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()}

# --- AUTH ENDPOINTS ---

@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    logger.info(f"Register attempt: {req.email}")
    if not req.email or not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Email, Username, and Password are required.")
        
    dob_dt = None
    if req.dob:
        try:
            dob_dt = datetime.strptime(req.dob, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for DOB. Use YYYY-MM-DD")
            
    success, msg = create_user(
        name=req.name, 
        email=req.email, 
        username=req.username,
        password=req.password,
        gender=req.gender,
        dob=dob_dt
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return AuthResponse(
        success=True, 
        message=msg, 
        name=req.name,
        email=req.email, 
        username=req.username,
        gender=req.gender,
        dob=req.dob
    )

@app.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    logger.info(f"Login attempt: {req.email}")
    try:
        user = authenticate_user(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        
        return AuthResponse(
            success=True, 
            message="Login successful", 
            name=user['name'],
            email=user['email'], 
            username=user['username'],
            gender=user['gender'],
            dob=user['dob']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.post("/auth/reset-password", response_model=AuthResponse)
async def reset_password_endpoint(req: ResetPasswordRequest):
    if not req.email or not req.username or not req.new_password:
        raise HTTPException(status_code=400, detail="Email, username, and new password are required.")
    
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    
    success, msg = reset_password(req.email, req.username, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return AuthResponse(
        success=True,
        message=msg,
        email=req.email,
        username=req.username
    )

# --- LEGAL SEARCH ENDPOINTS ---

def _fetch_internal(query, resources):
    try:
        query_embedding = resources.model.encode([query]).astype('float32')
        distances, indices = resources.index.search(query_embedding, 5)
        
        internal_context = []
        for idx in indices[0]:
            if idx == -1: continue
            data = resources.metadata[idx]
            internal_context.append(f"ACT: {data['act_name']}, SECTION: {data['section_number']} - {data['section_title']}\nTEXT: {data['text']}")
        return internal_context
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []

def _fetch_web_sync(query):
    try:
        with DDGS() as ddgs:
            full_query = f"{query} Motor Vehicles Act India 2024 2025"
            results = ddgs.text(full_query, max_results=2)
            web_results = [f"Title: {r['title']}\nSnippet: {r['body']}" for r in results]
            return "\n\n".join(web_results)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return ""

@app.post("/legal/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    loop = asyncio.get_event_loop()
    
    # Run vector search in executor
    internal_task = loop.run_in_executor(resources.executor, _fetch_internal, req.query, resources)
    
    web_context = ""
    if req.enable_web:
        web_task = loop.run_in_executor(resources.executor, _fetch_web_sync, req.query)
        try:
            internal_context, web_context = await asyncio.gather(
                internal_task,
                asyncio.wait_for(web_task, timeout=5.0)
            )
        except Exception:
            internal_context = await internal_task
            web_context = ""
    else:
        internal_context = await internal_task

    try:
        system_prompt = (
            "You are 'CivicAI', a specialized Indian Legal Intelligence Assistant.\n"
            "Domain: Indian Motor Vehicles Act, traffic laws, RC/DL, insurance, and road regulations.\n"
            "Rule: If query is off-topic, refuse politely. If sensitive, be neutral and cite MVA sections.\n"
            "Format: Cite Legal Section, Bullet points, Penalty, Recent Updates, and Disclaimer.\n\n"
            "CONTEXT:\n" + "\n".join(internal_context) + "\n\nWEB UPDATES:\n" + web_context
        )

        completion = await resources.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.query}
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        raise HTTPException(status_code=500, detail="AI processing failed.")
    
    return SearchResponse(answer=answer, sources=internal_context)

# --- CONFLICT MONITOR ENDPOINTS ---

@app.post("/conflict/analyze", response_model=ConflictReport)
async def analyze_conflict(
    party_a: str = Form(...),
    party_b: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    try:
        class FileMock:
            def __init__(self, upload_file: UploadFile, content: bytes):
                self.type = upload_file.content_type
                self.content = content
            def getvalue(self): return self.content

        processed_files = []
        if files:
            for f in files:
                content = await f.read()
                processed_files.append(FileMock(f, content))

        # Conflict processor should be run in executor if it's CPU heavy
        report = await resources.conflict_processor.process_conflict(party_a, party_b, files=processed_files)
        return report
    except Exception as e:
        logger.error(f"Conflict Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Use PORT environment variable if available (required for many cloud platforms)
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"📡 Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
