from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uvicorn
import json
import os
from datetime import datetime, timezone
import traceback
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio

from database import authenticate_user, create_user, init_db, get_session
from api_models import (
    LoginRequest, RegisterRequest, AuthResponse, 
    SearchRequest, SearchResponse, ConflictReport
)
from config import GROQ_API_KEY

# import faiss, pickle, and ConflictProcessor removed for lazy loading
from groq import AsyncGroq
from duckduckgo_search import DDGS

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and load AI models on startup."""
    logger.info("Starting up CivicAI API...")
    try:
        init_db()
        logger.info("Database initialized.")
        # Eagerly load AI resources to prevent first-request timeout
        await resources.load_all()
        logger.info("AI Resources (Model, Index, Metadata) loaded successfully.")
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        logger.error(traceback.format_exc())
    yield
    logger.info("Shutting down CivicAI API.")

app = FastAPI(title="Legal AI API", version="1.0.0", lifespan=lifespan)

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
    allow_origins=["*"], # Allow all for development to prevent emulator timeouts
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- Project root for absolute file paths (M7 fix) ---
_ROOT = os.path.dirname(os.path.abspath(__file__))

# Global Resources Singleton
class APIResources:
    def __init__(self):
        logger.info("API resources singleton initialized.")
        self.groq_key = GROQ_API_KEY
        self._index = None
        self._metadata = None
        self._model = None
        self.groq_client = AsyncGroq(api_key=self.groq_key)
        self.processor = None
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def load_all(self):
        """Eagerly load all heavy resources."""
        loop = asyncio.get_event_loop()
        
        # Load FAISS and Metadata in parallel using threads to not block the event loop
        tasks = [
            loop.run_in_executor(self.executor, self._load_index),
            loop.run_in_executor(self.executor, self._load_metadata),
            loop.run_in_executor(self.executor, self._load_model)
        ]
        await asyncio.gather(*tasks)

    def _load_index(self):
        if self._index is None:
            import faiss
            path = os.path.join(_ROOT, 'motor_vehicles.faiss')
            if os.path.exists(path):
                self._index = faiss.read_index(path)
                logger.info("FAISS index loaded.")

    def _load_metadata(self):
        if self._metadata is None:
            import pickle
            path = os.path.join(_ROOT, 'motor_vehicles_metadata.pkl')
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    self._metadata = pickle.load(f)
                logger.info("Metadata loaded.")

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            # This takes 1-2 mins normally
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

# --- AUTH ENDPOINTS ---

@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    logger.info(f"Register attempt for: {req.email}")
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
    logger.info(f"Login attempt for: {req.email}")
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

# --- LEGAL SEARCH ENDPOINTS ---

def _fetch_internal(query, resources):
    """CPU-bound vector search - run in thread."""
    try:
        # Encoding is CPU heavy
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
    """IO-bound web search - run in thread for compatibility."""
    try:
        with DDGS() as ddgs:
            full_query = f"{query} Motor Vehicles Act India 2024 2025"
            results = ddgs.text(full_query, max_results=2)
            web_results = [f"Title: {r['title']}\nSnippet: {r['body']}" for r in results]
            return "\n\n".join(web_results)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return "Web search results unavailable."

@app.post("/legal/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    loop = asyncio.get_event_loop()

    # 1. Parallel Context Fetch
    # Internal context (vector search) runs in global thread pool
    internal_task = loop.run_in_executor(resources.executor, _fetch_internal, req.query, resources)
    
    web_context = ""
    if req.enable_web:
        # Web search runs as a thread task
        web_task = loop.run_in_executor(resources.executor, _fetch_web_sync, req.query)
        
        # Run both in parallel
        try:
            # We wait for both, but cap web search at 4 seconds
            internal_context, web_context = await asyncio.gather(
                internal_task,
                asyncio.wait_for(web_task, timeout=4.0)
            )
        except asyncio.TimeoutError:
            internal_context = await internal_task
            web_context = "Web search timed out."
        except Exception as e:
            logger.error(f"Parallel fetch error: {e}")
            internal_context = await internal_task
            web_context = "Web search failed."
    else:
        internal_context = await internal_task

    # 2. LLM Completion
    try:
        system_prompt = (
            "You are 'CivicAI', a specialized Indian Legal Intelligence Assistant.\n"
            "Your ONLY domain is: Indian Motor Vehicles Act 1988 (MVA 1988), CMVR "
            "(Central Motor Vehicles Rules), Indian Traffic Laws, road accident laws, "
            "vehicle registration/RC, driving licences, motor insurance law, and "
            "traffic penalty/challan rules.\n\n"

            "═══ RULE 1: STRICT SCOPE ENFORCEMENT ═══\n"
            "If the user asks about ANYTHING outside your domain — including but not limited to: "
            "criminal law (IPC/BNS), politics, religion, medicine, relationships, finance, "
            "violence, weapons, hacking, cooking, entertainment, or any general knowledge — "
            "you MUST respond ONLY with this exact message:\n"
            "\"⚠️ I'm CivicAI, specialized exclusively in Indian Motor Vehicles Act, traffic laws, "
            "and road regulations. I'm unable to assist with this topic. "
            "Please consult the appropriate professional or authority.\"\n"
            "NEVER attempt to answer off-topic queries, even if they seem harmless.\n\n"

            "═══ RULE 2: SENSITIVE TOPIC NEUTRALITY ═══\n"
            "For sensitive in-domain topics (e.g. road accident deaths, hit-and-run fatalities, "
            "DUI deaths, accident compensation, grief-related queries, insurance after accident):\n"
            "- Respond with FACTUAL, NEUTRAL, COMPASSIONATE language only\n"
            "- Cite the exact MVA section (e.g. Section 161 for hit-and-run compensation)\n"
            "- Do NOT assign blame, make emotional judgments, or speculate\n"
            "- Always end sensitive answers with: "
            "'For official proceedings or compensation claims, please consult a qualified legal professional.'\n\n"

            "═══ RULE 3: REFUSE HARMFUL / EVASION QUERIES ═══\n"
            "Firmly refuse and cite relevant law if the query seems designed to:\n"
            "- Evade challan/traffic enforcement (e.g. 'how to avoid fine without paying')\n"
            "- Falsify vehicle documents (RC, DL, insurance, PUC)\n"
            "- Encourage reckless or dangerous driving\n"
            "- Exploit legal loopholes for fraud\n"
            "Respond: '⚠️ This falls outside the scope of lawful legal guidance. "
            "[Relevant Section] of MVA 1988 penalizes such actions.' Then state the penalty.\n\n"

            "═══ RULE 4: LANGUAGE MATCHING ═══\n"
            "Detect the user's language from their message and reply in the SAME language:\n"
            "- English query → English response\n"
            "- Hindi query → Hindi response\n"
            "- Hinglish (mixed) → Professional Hinglish with legal terms cited in English\n\n"

            "═══ RULE 5: RESPONSE FORMAT (for valid queries) ═══\n"
            "Always structure valid answers as:\n"
            "**📖 Legal Citation** — Act name + Section number\n"
            "**📋 Key Points** — Bullet-point summary (3-5 points max)\n"
            "**💰 Penalty / Fine** — Exact amount or range from the Act\n"
            "**🔄 Recent Update** — 2024-2025 amendment if available from WEB DATA\n"
            "**⚠️ Disclaimer** — End every answer with: "
            "'This is AI-generated legal information based on MVA 1988. "
            "For official legal advice, consult a qualified lawyer or your local RTO.'\n\n"

            "INTERNAL DATABASE CONTEXT (primary source):\n"
            + "\n".join(internal_context)
            + "\n\nWEB DATA (2024-2025 updates only):\n"
            + web_context
        )

        completion = await resources.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Faster model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.query}
            ],
            temperature=0.05,
            max_tokens=800,  # Optimized token count
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as e:
        return SearchResponse(answer=f"Error in LLM Completion: {str(e)}", sources=internal_context)
    
    return SearchResponse(answer=answer, sources=internal_context)

@app.get("/health")
async def health_check():
    return {"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()}

# --- CONFLICT MONITOR ENDPOINTS ---

@app.post("/conflict/analyze", response_model=ConflictReport)
async def analyze_conflict(
    party_a: str = Form(...),
    party_b: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    try:
        # Re-using the ConflictProcessor logic
        # We need to wrap UploadFiles into a simple object for the processor
        class FileMock:
            def __init__(self, upload_file: UploadFile):
                self.type = upload_file.content_type
                self.content = None
            def getvalue(self):
                return self.content

        processed_files = []
        if files:
            for f in files:
                fm = FileMock(f)
                fm.content = await f.read()
                processed_files.append(fm)

        report = await resources.conflict_processor.process_conflict(party_a, party_b, files=processed_files)
        if not report:
            raise HTTPException(status_code=500, detail="Engine failed to generate report")
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
