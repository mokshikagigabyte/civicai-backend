import streamlit as st
import base64
from datetime import datetime
from database import authenticate_user, create_user, init_db, get_session, User, ConflictSession, AnalysisResult
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq
from duckduckgo_search import DDGS
import streamlit.components.v1 as components
from conflic_model.processor import ConflictProcessor
from conflic_model.pdf_generator import LegalPDFGenerator
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# --- Constants & Config ---
GROQ_API_KEY = None  # Loaded lazily from config

# Page Config
st.set_page_config(page_title="Legal & Conflict Pro", page_icon="⚖️", layout="wide")

# --- UI Styling (Premium Midnight Gold) ---
def apply_styling():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    /* Splash Screen Overlay */
    #splash-screen {
        position: fixed;
        width: 100vw;
        height: 100vh;
        background: #0f172a;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        animation: fadeOut 3s forwards;
        pointer-events: none;
    }
    
    .pulse-logo {
        font-size: 5rem;
        font-weight: 600;
        color: #facc15;
        text-shadow: 0 0 20px rgba(250, 204, 21, 0.5);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(1); opacity: 0.8; }
    }
    
    @keyframes fadeOut {
        0% { opacity: 1; visibility: visible; }
        80% { opacity: 1; }
        100% { opacity: 0; visibility: hidden; }
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background: #0f172a !important;
        color: #f8fafc;
    }
    
    /* Sidebar glass effect */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(250, 204, 21, 0.2);
    }
    
    /* Card Glassmorphism */
    .glass-card {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(250, 204, 21, 0.1);
        border-radius: 20px;
        padding: 28px;
        margin-bottom: 24px;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border: 1px solid rgba(250, 204, 21, 0.4);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Custom Input Styling */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(250, 204, 21, 0.2) !important;
        color: white !important;
        border-radius: 12px !important;
    }
    
    /* Button Premium Gold Styling */
    .stButton > button {
        background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important;
        border: none !important;
        color: #0f172a !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(250, 204, 21, 0.3);
    }
    
    h1, h2, h3 {
        color: #facc15 !important;
        font-weight: 600 !important;
    }
    
    .stMarkdown p {
        color: #cbd5e1;
    }
    
    /* Circular Avatar Styling */
    .avatar-container {
        display: flex;
        justify-content: center;
        align-items: center;
        position: relative;
        width: 150px;
        height: 150px;
        margin: auto;
    }
    
    .circular-avatar {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #facc15;
        box-shadow: 0 4px 15px rgba(250, 204, 21, 0.3);
    }
    
    .edit-icon-overlay {
        position: absolute;
        bottom: 5px;
        right: 5px;
        background: #facc15;
        color: #0f172a;
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        border: 2px solid #0f172a;
    }

    .recent-searches-box {
        background: rgba(30, 41, 59, 0.3);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(250, 204, 21, 0.1);
        margin-top: 20px;
    }
    
    .suggestion-chip {
        display: inline-block;
        padding: 5px 12px;
        background: rgba(250, 204, 21, 0.1);
        border: 1px solid rgba(250, 204, 21, 0.3);
        border-radius: 20px;
        margin: 5px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: 0.3s;
    }
    .suggestion-chip:hover {
        background: rgba(250, 204, 21, 0.3);
    }
    
    /* Clickable Card Styling */
    div.stButton > button.card-btn {
        background: rgba(30, 41, 59, 0.5) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(250, 204, 21, 0.1) !important;
        border-radius: 20px !important;
        padding: 40px !important;
        width: 100% !important;
        height: 200px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        color: #facc15 !important;
        font-size: 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button.card-btn:hover {
        border: 1px solid rgba(250, 204, 21, 0.6) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
        transform: translateY(-5px) !important;
    }

    </style>
    <div id="splash-screen">
        <div class="pulse-logo">CivicAI</div>
        <div style="color: #facc15; margin-top: 20px; letter-spacing: 2px;">PREMIUM LEGAL INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)

# --- Resource Loading ---
@st.cache_resource(show_spinner=False)
def load_rag_resources():
    from config import GROQ_API_KEY as _KEY
    import os
    try:
        # Check if files exist before loading
        if not os.path.exists('motor_vehicles.faiss') or not os.path.exists('motor_vehicles_metadata.pkl'):
            logger.error("RAG resource files missing!")
            return None, None, None, Groq(api_key=_KEY)

        index = faiss.read_index('motor_vehicles.faiss')
        with open('motor_vehicles_metadata.pkl', 'rb') as f:
            metadata = pickle.load(f)
        
        # This is a large model, cache it
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        client = Groq(api_key=_KEY)
        logger.info("✅ RAG resources loaded successfully.")
        return index, metadata, model, client
    except Exception as e:
        logger.error(f"❌ RAG init issue: {e}")
        return None, None, None, Groq(api_key=_KEY)

# --- Authentication Logic ---
def auth_module():
    if "user" not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            mode = st.tabs(["Login", "Register"])
            
            with mode[0]:
                st.subheader("Login to Pro Dashboard")
                email = st.text_input("Email", key="l_email")
                password = st.text_input("Password", type="password", key="l_pass")
                if st.button("Login"):
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials or Database disconnected.")
            
            with mode[1]:
                st.subheader("Create Account")
                new_name = st.text_input("Name")
                new_email = st.text_input("Email")
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                new_gender = st.selectbox("Gender", ["Other", "Male", "Female"])
                new_dob = st.date_input("Date of Birth", min_value=datetime(1940, 1, 1))
                
                if st.button("Register"):
                    if not new_email or not new_user or not new_pass:
                        st.error("Email, Username and Password are required!")
                    else:
                        success, msg = create_user(
                            name=new_name, 
                            email=new_email, 
                            username=new_user, 
                            password=new_pass,
                            gender=new_gender,
                            dob=new_dob
                        )
                        if success:
                            st.success(msg)
                            # Auto-login after registration
                            user = authenticate_user(new_email, new_pass)
                            if user:
                                st.session_state.user = user
                                st.rerun()
                        else:
                            st.error(f"Registration failed: {msg}")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

# --- Voice Input Helper ---
def voice_input_component(key):
    # Specialized JS for Web Speech API
    voice_js = f"""
    <div id="voice-trigger-{key}" style="cursor: pointer; background: #facc15; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border: 2px solid #0f172a;">
        🎤
    </div>
    <script>
        const trigger = document.getElementById('voice-trigger-{key}');
        trigger.onclick = () => {{
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'en-IN'; // Multilingual default for India
            recognition.start();
            recognition.onresult = (event) => {{
                const transcript = event.results[0][0].transcript;
                window.parent.postMessage({{
                    type: 'streamlit:set_widget_value',
                    key: '{key}',
                    value: transcript
                }}, '*');
            }};
        }};
    </script>
    """
    components.html(voice_js, height=50)

# --- Application Modules ---

def legal_assistant_module(index, metadata, model, groq_client):
    st.title("⚖️ Legal Assistant Pro")
    st.markdown("### Official Data & Live Web Intelligence")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []

    # Sidebar History (Optional: can be in main too)
    with st.sidebar:
        st.markdown("<div class='recent-searches-box'>", unsafe_allow_html=True)
        st.markdown("#### 🕒 Recent Searches")
        if not st.session_state.history:
            st.write("No history yet.")
        for h in st.session_state.history[-5:]:
            if st.button(f"🔍 {h[:20]}...", key=f"hist_{h}"):
                # This could trigger a re-search logic but for now just display
                pass
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Shared prompt builder — single source of truth for scope, safety, and format rules
    def _build_legal_prompt(int_text, web_text):
        return (
            "You are 'CivicAI', a specialized Indian Legal Intelligence Assistant.\n"
            "Your ONLY domain is: Indian Motor Vehicles Act 1988 (MVA 1988), CMVR "
            "(Central Motor Vehicles Rules), Indian Traffic Laws, road accident laws, "
            "vehicle registration/RC, driving licences, motor insurance law, and "
            "traffic penalty/challan rules.\n\n"

            "═══ RULE 1: STRICT SCOPE ENFORCEMENT ═══\n"
            "If the user asks about ANYTHING outside your domain — including but not limited to: "
            "criminal law, politics, religion, medicine, relationships, finance, "
            "violence, weapons, hacking, cooking, entertainment, or any general knowledge — "
            "you MUST respond ONLY with:\n"
            "'⚠️ Main sirf Indian Motor Vehicles Act, traffic laws aur road regulations ke baare mein "
            "help kar sakta hoon. Is topic mein main aapki madad karne mein asmarth hoon. "
            "Kripya uchit professional se sampark karein.'\n"
            "(Translate this refusal into the same language the user used.)\n"
            "NEVER answer off-topic queries, even if they seem harmless or related.\n\n"

            "═══ RULE 2: SENSITIVE TOPIC NEUTRALITY ═══\n"
            "For sensitive in-domain topics (road accident deaths, hit-and-run, DUI fatalities, "
            "compensation, insurance claims, grief queries):\n"
            "- Use FACTUAL, NEUTRAL, COMPASSIONATE language\n"
            "- Cite exact MVA section (e.g. Sec 161 for hit-and-run compensation)\n"
            "- Do NOT assign blame, speculate, or make emotional judgments\n"
            "- End with: 'Kisi bhi official claim ya karyavahi ke liye qualified legal professional "
            "se salah lein.' (in user's language)\n\n"

            "═══ RULE 3: REFUSE HARMFUL / EVASION QUERIES ═══\n"
            "Firmly refuse if query is designed to:\n"
            "- Evade challans or traffic fines without legal grounds\n"
            "- Falsify RC, DL, insurance, or PUC documents\n"
            "- Encourage reckless/dangerous driving\n"
            "- Exploit loopholes for fraud\n"
            "Respond: '⚠️ Ye request lawful legal guidance ke daayare se bahar hai. "
            "[Relevant Section] MVA 1988 ke anusaar aisi karwai penalizable hai.' + state the penalty.\n\n"

            "═══ RULE 4: LANGUAGE MATCHING ═══\n"
            "Detect and match the user's language exactly:\n"
            "- English → English  |  Hindi → Hindi  |  Hinglish → Professional Hinglish\n"
            "Legal terms (Section numbers, Act names) always cited in English.\n\n"

            "═══ RULE 5: RESPONSE FORMAT ═══\n"
            "For valid queries, structure the answer as:\n"
            "**📖 Legal Citation** — MVA 1988 Section + title\n"
            "**📋 Key Points** — 3-5 bullet points\n"
            "**💰 Penalty / Fine** — Exact amount from the Act\n"
            "**🔄 Recent Update** — 2024-2025 amendment if found in WEB DATA\n"
            "**⚠️ Disclaimer** — 'Ye AI-generated jankari hai. Official salah ke liye "
            "qualified vakeel ya apne nazdiki RTO se sampark karein.'\n\n"

            f"INTERNAL DATABASE (primary source):\n{int_text}\n\n"
            f"WEB DATA (2024-2025 updates only):\n{web_text}"
        )

    # ── In-memory query cache (instant reply for repeated questions) ──
    if "_legal_cache" not in st.session_state:
        st.session_state._legal_cache = {}
    _cache = st.session_state._legal_cache

    # ── Parallel fetch helper: FAISS + Web at the same time ──
    def _fetch_faiss(query):
        if not index:
            return "Internal database offline."
        q_emb = model.encode([query]).astype('float32')
        _, idxs = index.search(q_emb, 3)
        ctx = [
            f"Sec {metadata[i]['section_number']} — {metadata[i]['section_title']}:\n{metadata[i]['text']}"
            for i in idxs[0] if i != -1
        ]
        return "\n---\n".join(ctx) if ctx else "No matching sections found."

    def _fetch_web(query):
        try:
            with DDGS() as ddgs:
                results = [
                    f"Title: {r['title']}\nSummary: {r['body']}"
                    for r in ddgs.text(
                        query + " India Motor Vehicles Act 2024",
                        max_results=2,          # was 3 → 2 saves ~1s
                        timelimit='y',          # only results from past year
                    )
                ]
                return "\n\n".join(results)
        except:
            return ""  # web fail = silently skip, don't block response

    def _get_context_parallel(query):
        """Run FAISS + web search simultaneously. Max 3s for web."""
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_future  = ex.submit(_fetch_faiss, query)
            web_future = ex.submit(_fetch_web, query)
            int_text = f_future.result()          # FAISS is always fast
            try:
                web_text = web_future.result(timeout=3)  # web max 3s
            except FuturesTimeout:
                web_text = ""  # skip web if too slow
        return int_text, web_text

    # Shared live search (kept for backward compat, now wraps _fetch_web)
    def get_live_search(query):
        return _fetch_web(query)

    # Chat UI
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Voice Input for Assistant
    st.write("🎤 **Voice Search:**")
    voice_input_component("assistant_voice")
    if st.session_state.get("assistant_voice"):
        # If voice captured, use it as a prompt
        v_prompt = st.session_state.assistant_voice
        st.session_state.messages.append({"role": "user", "content": v_prompt})
        st.session_state.assistant_voice = "" # Reset
        st.rerun()

    if prompt := st.chat_input("Ask about traffic laws..."):
        cache_key = prompt.strip().lower()

        # ── Cache hit: instant reply ──
        if cache_key in _cache:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            cached_response = _cache[cache_key]
            st.session_state.messages.append({"role": "assistant", "content": cached_response})
            with st.chat_message("assistant"): st.markdown(cached_response)
            if prompt not in st.session_state.history:
                st.session_state.history.append(prompt)
            st.rerun()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        # ── Parallel FAISS + Web fetch ──
        with st.spinner("⚡ Fetching legal context..."):
            int_text, web_text = _get_context_parallel(prompt)

        # ── Streaming LLM ──
        with st.chat_message("assistant"):
            stream = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": _build_legal_prompt(int_text, web_text)},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.05,
                max_tokens=700,
                stream=True,
            )
            response = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in stream
            )

        _cache[cache_key] = response
        st.session_state.messages.append({"role": "assistant", "content": response})
        if prompt not in st.session_state.history:
            st.session_state.history.append(prompt)
        st.rerun()

    # Suggestions UI
    st.markdown("---")
    suggestions = ["Drink & Drive Penalty", "Helmet Rules 2024", "License Renewal Age", "Speeding Fine", "RC Transfer Process"]
    st.write("💡 **Suggested Topics:**")
    cols = st.columns(len(suggestions))
    for i, sug in enumerate(suggestions):
        if cols[i].button(sug, key=f"sug_{i}"):
            # Store the suggestion as a pending prompt to process in next rerun
            st.session_state.pending_suggestion = sug
            st.rerun()

    # Handle pending suggestion — process it as a full AI query
    if st.session_state.get("pending_suggestion"):
        sug_prompt = st.session_state.pending_suggestion
        del st.session_state.pending_suggestion
        cache_key = sug_prompt.strip().lower()

        # ── Cache hit: instant reply ──
        if cache_key in _cache:
            st.session_state.messages.append({"role": "user", "content": sug_prompt})
            st.session_state.messages.append({"role": "assistant", "content": _cache[cache_key]})
            st.rerun()

        st.session_state.messages.append({"role": "user", "content": sug_prompt})

        # ── Parallel FAISS + Web fetch ──
        with st.spinner("⚡ Fetching legal context..."):
            int_text, web_text = _get_context_parallel(sug_prompt)

        # ── Streaming LLM ──
        with st.chat_message("assistant"):
            stream = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": _build_legal_prompt(int_text, web_text)},
                    {"role": "user",   "content": sug_prompt}
                ],
                temperature=0.05,
                max_tokens=700,
                stream=True,
            )
            response = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in stream
            )

        _cache[cache_key] = response
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
            
    # Download Button
    if st.session_state.messages:
        full_chat = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
        st.download_button("📥 Download Full Chat", full_chat, file_name="legal_consultation.txt")

def conflict_monitor_module(index, metadata, embed_model, groq_client):
    st.title("📊 Conflict Monitor")
    st.info("Input statements from two parties involved in a motor vehicle dispute to analyze violations.")
    
    # Initialize session state
    if "conflict_report" not in st.session_state:
        st.session_state.conflict_report = None
    if "conflict_report_pdf" not in st.session_state:
        st.session_state.conflict_report_pdf = None

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        party_a = st.text_area("Party A Statement", placeholder="I was driving straight when...", height=150, key="p_a_text")
        st.write("🎤 Voice Input:")
        voice_input_component("p_a_text")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        party_b = st.text_area("Party B Statement", placeholder="He came out of nowhere and...", height=150, key="p_b_text")
        st.write("🎤 Voice Input:")
        voice_input_component("p_b_text")
        st.markdown("</div>", unsafe_allow_html=True)

    # Optional evidence upload
    uploaded_files = st.file_uploader(
        "📎 Attach Evidence (Images/Videos - Optional)",
        type=["jpg", "jpeg", "png", "mp4", "mov"],
        accept_multiple_files=True,
        key="conflict_evidence"
    )
        
    if st.button("🔍 Run Conflict Analysis", use_container_width=True):
        p_a_val = st.session_state.get("p_a_text", "").strip()
        p_b_val = st.session_state.get("p_b_text", "").strip()
        if p_a_val and p_b_val:
            with st.spinner("🧠 Analyzing behavior, legal context & evidence..."):
                try:
                    from config import GROQ_API_KEY as _KEY
                    processor = ConflictProcessor(
                        groq_api_key=_KEY,
                        index=index,
                        metadata=metadata,
                        model=embed_model
                    )
                    report = processor.process_conflict(
                        party_a_text=p_a_val,
                        party_b_text=p_b_val,
                        files=uploaded_files if uploaded_files else None
                    )
                    st.session_state.conflict_report = report

                    # Pre-generate PDF bytes and store in session state
                    try:
                        pdf_gen = LegalPDFGenerator()
                        pdf_bytes = pdf_gen.generate_report(report)
                        st.session_state.conflict_report_pdf = bytes(pdf_bytes)
                    except Exception as pdf_err:
                        print(f"PDF generation error: {pdf_err}")
                        st.session_state.conflict_report_pdf = None

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    print(f"Conflict analysis error: {e}")
        else:
            st.warning("Please provide statements from both parties.")

    # --- Display persisted results (outside spinner — always visible) ---
    if st.session_state.conflict_report:
        report = st.session_state.conflict_report
        st.markdown("---")
        st.subheader("📋 Analysis Results")

        tab1, tab2, tab3, tab4 = st.tabs(["⚖️ Legal Verdict", "🧠 Behavior", "⚠️ Risk", "🤝 Resolution"])

        with tab1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(f"**🚨 Violation Detected:** {report.legal_analysis.detected_violation}")
            st.markdown(f"**📖 Relevant Section:** {report.legal_analysis.relevant_section} (MVA 1988)")
            st.markdown(f"**💰 Possible Penalty:** {report.legal_analysis.possible_penalty}")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("**Party A**")
                st.markdown(f"😐 Sentiment: `{report.behavior_analysis.party_a_sentiment}`")
                st.markdown(f"☣️ Toxicity: `{report.behavior_analysis.party_a_toxicity}`")
                st.markdown("</div>", unsafe_allow_html=True)
            with col_b:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("**Party B**")
                st.markdown(f"😐 Sentiment: `{report.behavior_analysis.party_b_sentiment}`")
                st.markdown(f"☣️ Toxicity: `{report.behavior_analysis.party_b_toxicity}`")
                st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("**Party A Legal Risk**")
                st.info(report.legal_risk_assessment.party_a_legal_risk)
                st.markdown("</div>", unsafe_allow_html=True)
            with col_b:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("**Party B Legal Risk**")
                st.info(report.legal_risk_assessment.party_b_legal_risk)
                st.markdown("</div>", unsafe_allow_html=True)

        with tab4:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(f"**✅ Suggested Action:** {report.resolution_suggestion.suggested_legal_action}")
            st.markdown(f"**🤝 Mediation Advice:** {report.resolution_suggestion.suggested_mediation_advice}")
            st.markdown(f"**🛡️ Preventive Advice:** {report.resolution_suggestion.preventive_advice}")
            st.markdown("</div>", unsafe_allow_html=True)

        # --- Persistent Download Buttons ---
        st.markdown("---")
        st.subheader("📥 Download Report")
        dl_col1, dl_col2 = st.columns(2)
        
        with dl_col1:
            # Plain text/markdown report
            text_report = f"""# Legal Conflict Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Legal Verdict
- **Violation:** {report.legal_analysis.detected_violation}
- **Section:** {report.legal_analysis.relevant_section} (MVA 1988)
- **Penalty:** {report.legal_analysis.possible_penalty}

## Behavior Analysis
### Party A
- Sentiment: {report.behavior_analysis.party_a_sentiment}
- Toxicity: {report.behavior_analysis.party_a_toxicity}

### Party B
- Sentiment: {report.behavior_analysis.party_b_sentiment}
- Toxicity: {report.behavior_analysis.party_b_toxicity}

## Legal Risk Assessment
- Party A Risk: {report.legal_risk_assessment.party_a_legal_risk}
- Party B Risk: {report.legal_risk_assessment.party_b_legal_risk}

## Resolution
- Suggested Action: {report.resolution_suggestion.suggested_legal_action}
- Mediation Advice: {report.resolution_suggestion.suggested_mediation_advice}
- Preventive Advice: {report.resolution_suggestion.preventive_advice}

---
Disclaimer: AI-generated analysis. Not formal legal advice.
"""
            st.download_button(
                label="📄 Download as Markdown",
                data=text_report,
                file_name=f"conflict_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )

        with dl_col2:
            if st.session_state.conflict_report_pdf:
                st.download_button(
                    label="📑 Download PDF Report",
                    data=st.session_state.conflict_report_pdf,
                    file_name=f"conflict_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.info("PDF generation unavailable (fpdf2 not installed)")

def profile_module():
    st.title("👤 User Profile")
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    
    # Circular Avatar logic
    img_url = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png" # Default
    if st.session_state.user.get("profile_image"):
        img_url = st.session_state.user["profile_image"]

    st.markdown(f"""
        <div class="avatar-container">
            <img src="{img_url}" class="circular-avatar">
            <div class="edit-icon-overlay">✏️</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<h2 style='text-align: center;'>{st.session_state.user['name']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #acc1fa;'>@{st.session_state.user['username']}</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.text_input("Full Name", value=st.session_state.user['name'] if st.session_state.user else "")
        st.selectbox("Gender", ["Male", "Female", "Other"], index=0 if st.session_state.user['gender'] == 'Male' else (1 if st.session_state.user['gender'] == 'Female' else 2))
    
    with col2:
        st.text_input("Email Address", value=st.session_state.user['email'] if st.session_state.user else "", disabled=True)
        st.date_input("Date of Birth", value=datetime.strptime(st.session_state.user['dob'], "%Y-%m-%d") if st.session_state.user['dob'] else datetime.now())
    
    if st.button("Update Profile Info"):
        st.success("Profile updated successfully!")
    
    st.markdown("---")
    st.subheader("Change Profile Image")
    # Hide the uploader inside an expander or just keep it simple
    with st.expander("Update Avatar"):
        uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="avatar_uploader")
        if uploaded_file:
            st.info("Image processing feature in next build.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# --- Main App Logic ---

def main():
    # Initialize database tables on startup
    try:
        init_db()
    except Exception as e:
        st.error(f"Critical: Database connection failed. {e}")
        return

    apply_styling()
    
    if not auth_module():
        return

    # Sidebar Navigation
    with st.sidebar:
        user_display_name = st.session_state.user['name'].split()[0] if st.session_state.user else "User"
        st.markdown(f"### Hello, {user_display_name}")
        
        # Sync navigation with card clicks
        options = ["Home", "Legal Assistant", "Conflict Monitor", "My Profile", "Settings"]
        if "nav_choice" not in st.session_state:
            st.session_state.nav_choice = "Home"
            
        nav = st.radio("Navigation", options, index=options.index(st.session_state.nav_choice))
        st.session_state.nav_choice = nav
        
        st.divider()
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    # Load resources after auth
    index, metadata, model, groq_client = load_rag_resources()

    if st.session_state.nav_choice == "Home":
        st.title("🚀 CivicAI Intelligence Hub")
        st.markdown(f"""
        <div class='glass-card' style='text-align: center;'>
            <h2 style='color: #facc15;'>Welcome back, {user_display_name}!</h2>
            <p>Your premium legal assistant and conflict monitor are ready. Access the modules below or use the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚖️ Open Legal Assistant", key="launch_assistant", help="Ask about traffic laws...", use_container_width=True):
                st.session_state.nav_choice = "Legal Assistant"
                st.rerun()
            st.markdown("<p style='text-align:center;'>Penalty Lookups & Section Details</p>", unsafe_allow_html=True)
            
        with col2:
            if st.button("📊 Open Conflict Monitor", key="launch_conflict", help="Analyze traffic disputes...", use_container_width=True):
                st.session_state.nav_choice = "Conflict Monitor"
                st.rerun()
            st.markdown("<p style='text-align:center;'>Violation Analysis & Dispute Resolution</p>", unsafe_allow_html=True)
            
    elif st.session_state.nav_choice == "Legal Assistant":
        legal_assistant_module(index, metadata, model, groq_client)
    elif st.session_state.nav_choice == "Conflict Monitor":
        conflict_monitor_module(index, metadata, model, groq_client)
    elif st.session_state.nav_choice == "My Profile":
        profile_module()
    elif st.session_state.nav_choice == "Settings":
        st.subheader("App Settings")
        st.info("Additional settings coming soon.")

if __name__ == "__main__":
    main()
