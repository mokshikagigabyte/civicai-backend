# CivicAI - Premium Legal Intelligence Backend

CivicAI is a specialized AI-powered backend designed for the Indian Motor Vehicles Act (MVA 1988) and traffic regulations. It provides a RAG-based Legal Assistant and a Conflict Monitor for analyzing road accident disputes.

## 🚀 Deployment Features

- **Robust Database Layer**: Optimized for PostgreSQL (Supabase, RDS) with automatic SSL handling and connection pooling.
- **Dual Interface**: 
  - **FastAPI**: High-performance REST API for mobile/web clients.
  - **Streamlit**: Premium internal dashboard for data visualization and analysis.
- **RAG Pipeline**: Vector search using FAISS and SentenceTransformers for precise legal citations.
- **Cloud Ready**: Configured for Render, Railway, and Heroku with dynamic port handling.

## 🛠️ Setup Instructions

1. **Install Dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Copy `.env.example` to `.env` and fill in your credentials:
   - `DATABASE_URL` or individual `DB_*` components.
   - `GROQ_API_KEY` for LLM processing.

3. **Run Locally**:
   - **Backend API**: `python main.py` (Runs on port 8000)
   - **Dashboard**: `streamlit run main_app.py` (Runs on port 8501)
   - **Integrated Launcher**: `python launcher.py` (Starts both services)

## 📁 Repository Structure

- `main.py`: FastAPI entry point.
- `main_app.py`: Streamlit Dashboard.
- `database.py`: SQLAlchemy models and session management.
- `conflic_model/`: Core logic for conflict analysis and legal RAG.
- `motor_vehicles.faiss`: Pre-built vector index for MVA.

---
Developed by **CivicAI Team**