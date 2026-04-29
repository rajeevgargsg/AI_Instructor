"""
Algorithmic Instructional Designer — Streamlit App
====================================================
Run:  streamlit run app.py
"""

import os
import pathlib
import time

import streamlit as st
from dotenv import load_dotenv

from sdk import (
    GenerationConfig,
    LearnerProfile,
    LessonArtifacts,
    LessonController,
    PROFILE_LABELS,
)
from sdk.pdf_generator import artifacts_to_pdf_bytes

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Algorithmic Instructional Designer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Hero header ─────────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B4332 50%, #00897B 100%);
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.8rem;
    color: white;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -40%; right: -10%;
    width: 320px; height: 320px;
    background: rgba(255,255,255,0.04);
    border-radius: 50%;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 .4rem; letter-spacing: -0.5px; }
.hero p  { font-size: .95rem; opacity: .82; margin: 0; }
.hero .badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: .25rem .8rem;
    font-size: .78rem;
    font-weight: 600;
    margin-right: .5rem;
    backdrop-filter: blur(4px);
}

/* ── Pipeline diagram ────────────────────────────────────────────────── */
.pipeline-wrap {
    background: #F8FAFB;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.6rem 1.2rem;
    margin-bottom: 1.6rem;
}
.pipeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    flex-wrap: wrap;
}
.agent-node {
    background: white;
    border: 2px solid #E2E8F0;
    border-radius: 12px;
    padding: .9rem 1.1rem;
    text-align: center;
    min-width: 108px;
    transition: all .3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.agent-node .icon   { font-size: 1.6rem; display: block; margin-bottom: .25rem; }
.agent-node .label  { font-size: .78rem; font-weight: 600; color: #334155; display: block; }
.agent-node .status { font-size: .7rem;  color: #94A3B8;   display: block; margin-top: .2rem; }

.agent-node.waiting  { border-color: #E2E8F0; }
.agent-node.running  { border-color: #F59E0B; background: #FFFBEB;
                        box-shadow: 0 0 0 3px rgba(245,158,11,.2); }
.agent-node.done     { border-color: #10B981; background: #F0FDF4;
                        box-shadow: 0 0 0 3px rgba(16,185,129,.15); }
.agent-node.error    { border-color: #EF4444; background: #FEF2F2; }

.agent-node.running .status { color: #D97706; font-weight: 600; }
.agent-node.done    .status { color: #059669; font-weight: 600; }

.arrow {
    font-size: 1.3rem; color: #94A3B8;
    padding: 0 .4rem;
    flex-shrink: 0;
    align-self: center;
}

/* ── Cards ───────────────────────────────────────────────────────────── */
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.4rem;
}
.metric-card {
    flex: 1;
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,.05);
}
.metric-card .value {
    font-size: 1.9rem; font-weight: 700; color: #0D1B2A;
    display: block; line-height: 1;
}
.metric-card .label {
    font-size: .78rem; color: #64748B;
    font-weight: 500; margin-top: .35rem; display: block;
}
.metric-card.pass  .value { color: #059669; }
.metric-card.fail  .value { color: #DC2626; }
.metric-card.info  .value { color: #2563EB; }
.metric-card.warn  .value { color: #D97706; }

/* ── Section label ───────────────────────────────────────────────────── */
.section-label {
    font-size: .72rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #64748B;
    margin-bottom: .6rem;
}

/* ── Attempt badge ───────────────────────────────────────────────────── */
.attempt-badge {
    display: inline-flex; align-items: center; gap: .4rem;
    background: #EFF6FF; border: 1px solid #BFDBFE;
    border-radius: 8px; padding: .35rem .75rem;
    font-size: .82rem; font-weight: 600; color: #1D4ED8;
    margin: .2rem;
}
.attempt-badge.pass { background: #F0FDF4; border-color: #BBF7D0; color: #166534; }
.attempt-badge.fail { background: #FEF2F2; border-color: #FECACA; color: #991B1B; }

/* ── Sidebar tweaks ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #0D1B2A; }
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stTextArea label { color: #94A3B8 !important; font-size: .82rem !important; font-weight: 500 !important; }
[data-testid="stSidebar"] hr { border-color: #1E3A5F !important; }
[data-testid="stSidebar"] .sidebar-section-title {
    font-size: .72rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #00897B !important;
    margin: 1rem 0 .4rem;
}

/* ── Tabs ────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab"] { font-weight: 600; font-size: .88rem; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: #00897B; }

/* ── Download button row ─────────────────────────────────────────────── */
.dl-section {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-top: 1.2rem;
}
.dl-title { font-weight: 700; color: #166534; font-size: .9rem; margin-bottom: .8rem; }

/* ── Progress log ────────────────────────────────────────────────────── */
.log-box {
    background: #0D1B2A;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: .8rem;
    color: #94A3B8;
    max-height: 220px;
    overflow-y: auto;
    line-height: 1.7;
}
.log-box .log-done  { color: #34D399; }
.log-box .log-run   { color: #FCD34D; }
.log-box .log-warn  { color: #F87171; }
.log-box .log-info  { color: #93C5FD; }

/* ── Info banner ─────────────────────────────────────────────────────── */
.info-banner {
    background: #EFF6FF;
    border-left: 4px solid #3B82F6;
    border-radius: 0 8px 8px 0;
    padding: .9rem 1.1rem;
    font-size: .88rem;
    color: #1E40AF;
    margin-bottom: 1rem;
}

/* ── How-it-works cards ──────────────────────────────────────────────── */
.how-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-top: 3px solid #00897B;
    border-radius: 10px;
    padding: 1.1rem;
    height: 100%;
}
.how-card .num  { font-size: 1.5rem; font-weight: 800; color: #00897B; }
.how-card .ttl  { font-size: .9rem; font-weight: 700; color: #0D1B2A; margin: .3rem 0 .4rem; }
.how-card .desc { font-size: .82rem; color: #475569; line-height: 1.5; }

/* ── Spinner override ────────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #00897B !important; }

/* ── Button ──────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00897B, #00695C);
    border: none; color: white; font-weight: 700;
    border-radius: 10px; padding: .65rem 1.5rem;
    transition: all .2s;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(0,137,123,.4);
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = dict(
    artifacts=None,
    iter_log=[],
    pdf_bytes={},
    running=False,
    log_messages=[],
    agent_states={},
    total_seconds=0,
    error=None,
)
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Pipeline Diagram HTML
# ─────────────────────────────────────────────────────────────────────────────
_AGENT_DEFS = [
    ("📄", "Source",    "source"),
    ("→",  "",          None),
    ("🏗️", "Architect", "architect"),
    ("→",  "",          None),
    ("📝", "Content",   "content"),
    ("→",  "",          None),
    ("🎓", "Student",   "student"),
    ("→",  "",          None),
    ("📚", "Artefacts", "output"),
]

_STATUS_LABELS = {
    "waiting": "Waiting",
    "running": "Running…",
    "done":    "Done ✓",
    "error":   "Error ✗",
}


def _pipeline_html(states: dict) -> str:
    nodes = []
    for icon, label, key in _AGENT_DEFS:
        if key is None:
            nodes.append(f'<div class="arrow">{icon}</div>')
        else:
            state  = states.get(key, "waiting")
            slabel = _STATUS_LABELS.get(state, "Waiting")
            nodes.append(
                f'<div class="agent-node {state}">'
                f'  <span class="icon">{icon}</span>'
                f'  <span class="label">{label}</span>'
                f'  <span class="status">{slabel}</span>'
                f'</div>'
            )
    return (
        '<div class="pipeline-wrap">'
        '  <div class="section-label">Pipeline</div>'
        '  <div class="pipeline">' + "".join(nodes) + "</div>"
        "</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Progress Log HTML
# ─────────────────────────────────────────────────────────────────────────────
def _log_html(messages: list) -> str:
    lines = []
    for m in messages[-18:]:
        if "DONE" in m or "✅" in m or "PASS" in m:
            cls, txt = "log-done", m.split("|")[-1]
        elif "START" in m or "RETRY" in m:
            cls, txt = "log-run", m.split("|")[-1]
        elif "ERROR" in m or "MAXRETRY" in m or "❌" in m:
            cls, txt = "log-warn", m.split("|")[-1]
        else:
            cls, txt = "log-info", m.split("|")[-1]
        lines.append(f'<div class="{cls}">&rsaquo; {txt}</div>')
    return '<div class="log-box">' + "\n".join(lines) + "</div>"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Agent state updater from pipeline messages
# ─────────────────────────────────────────────────────────────────────────────
def _update_agent_states(states: dict, msg: str):
    """Parse progress message tags and update agent state dict."""
    if   "ARCHITECT_START"  in msg: states.update({"architect": "running"})
    elif "ARCHITECT_DONE"   in msg: states.update({"architect": "done"})
    elif "CONTENT_LP_START" in msg or "CONTENT_SH_START" in msg or \
         "CONTENT_QZ_START" in msg or "CONTENT_AK_START" in msg:
        states.update({"content": "running"})
    elif "CONTENT_AK_DONE"  in msg: states.update({"content": "done"})
    elif "STUDENT_START"    in msg: states.update({"student": "running"})
    elif "STUDENT_DONE"     in msg: states.update({"student": "done",
                                                    "output":  "done"})
    elif "PIPELINE_RETRY"   in msg: states.update({"architect": "waiting",
                                                    "content":  "waiting",
                                                    "student":  "waiting",
                                                    "output":   "waiting"})


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Load source from uploaded files
# ─────────────────────────────────────────────────────────────────────────────
def _load_source(uploaded_files, pasted_text: str) -> str:
    source = pasted_text.strip()
    if uploaded_files:
        for f in (uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]):
            ext = pathlib.Path(f.name).suffix.lower()
            if ext == ".pdf":
                try:
                    import pdfplumber
                    import io
                    with pdfplumber.open(io.BytesIO(f.read())) as pdf:
                        source += "\n\n" + "\n".join(
                            p.extract_text() or "" for p in pdf.pages)
                except Exception as e:
                    st.warning(f"PDF parse error ({f.name}): {e}")
            else:
                source += "\n\n" + f.read().decode("utf-8", errors="ignore")
    return source


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:1rem 0 .5rem;">'
        '<span style="font-size:2.2rem">🎓</span>'
        '<div style="font-size:1.05rem;font-weight:700;margin-top:.3rem;">'
        'Instructional Designer</div>'
        '<div style="font-size:.75rem;opacity:.6;margin-top:.15rem;">'
        'Groq · LLaMA 3.3 70B</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── API Key ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">🔑 API Configuration</div>',
                unsafe_allow_html=True)
    api_key = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        placeholder="gsk_…",
        help="Get a free key at console.groq.com",
    )

    st.divider()

    # ── Topic ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">📌 Topic</div>',
                unsafe_allow_html=True)
    topic_title = st.text_input(
        "Title",
        value="Embeddings and Vector Databases",
    )
    topic_desc = st.text_area(
        "Description",
        value=(
            "How text is encoded as dense numeric vectors, "
            "cosine similarity, ANN search, and vector databases "
            "for semantic retrieval in RAG systems."
        ),
        height=90,
    )

    st.divider()

    # ── Learner Profile ──────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">👤 Learner Profile</div>',
                unsafe_allow_html=True)
    profile_str = st.selectbox(
        "Target audience",
        options=["Beginner", "MSc Student", "Product Manager"],
        index=1,
    )

    st.divider()

    # ── Quality Control ──────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">⚙️ Quality Control</div>',
                unsafe_allow_html=True)
    pass_threshold = st.slider(
        "Pass Threshold (%)",
        min_value=50, max_value=95, value=80, step=5,
        help="Simulated student must score this % to pass",
    )
    max_retries = st.slider(
        "Max Revision Retries",
        min_value=0, max_value=3, value=2,
        help="Times the pipeline will revise if student fails",
    )

    st.divider()

    # ── Source Material ──────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">📄 Source Material</div>',
                unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload .txt or .pdf",
        accept_multiple_files=True,
        type=["txt", "pdf"],
    )

    st.divider()

    # ── Generate Button ──────────────────────────────────────────────────────
    generate_btn = st.button(
        "🚀 Generate Lesson",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running,
    )

    # ── Previous Runs ────────────────────────────────────────────────────────
    if st.session_state.iter_log:
        st.divider()
        st.markdown('<div class="sidebar-section-title">📊 Last Run</div>',
                    unsafe_allow_html=True)
        for e in st.session_state.iter_log:
            badge_cls = "pass" if e["passed"] else "fail"
            icon      = "✅" if e["passed"] else "❌"
            st.markdown(
                f'<div class="attempt-badge {badge_cls}">'
                f'{icon} Attempt {e["attempt"]} — '
                f'{e["score_pct"]}% in {e["total_seconds"]}s</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────

# Hero header
st.markdown("""
<div class="hero">
  <span class="badge">Groq</span>
  <span class="badge">LLaMA 3.3 70B</span>
  <span class="badge">Multi-Agent</span>
  <h1>🎓 Algorithmic Instructional Designer</h1>
  <p>Transform raw technical documentation into structured pedagogical
     lesson materials using Gagne's Nine Events &amp; Merrill's First Principles.</p>
</div>
""", unsafe_allow_html=True)

# Source text area (main area, full width)
default_source = """Word Embeddings and Vector Representations
===========================================

Introduction
------------
Word embeddings are dense vector representations of words in a continuous
vector space where semantically similar words are mapped to nearby points.
Unlike one-hot encodings (sparse, high-dimensional), embeddings capture
semantic relationships between words.

Key Concept: Word2Vec
---------------------
Word2Vec (Mikolov et al., 2013) introduced two architectures:
  CBOW  (Continuous Bag-of-Words): predicts target word from context words.
  Skip-gram: predicts context words from a target word.
Both produce dense vectors typically 100-300 dimensions.

Mathematical Foundation
-----------------------
Given vocabulary V and embedding dimension d, learn matrix E in R^(|V|xd).
Similarity is measured with cosine similarity:
  cos(u,v) = (u dot v) / (||u|| * ||v||)
Range: -1 (opposite) to +1 (same direction).

Sentence Embeddings
-------------------
Sentence-BERT (SBERT): Fine-tuned BERT with siamese networks for sentence-level similarity.
OpenAI text-embedding-3-small / large: State-of-the-art general-purpose embeddings.
Dimensions: 768 (BERT-base), 1536 (ada-002), up to 3072 (text-embedding-3-large).

Vector Databases
----------------
Vector databases store and index high-dimensional vectors for Approximate
Nearest Neighbour (ANN) search at scale.

Popular systems:
  Pinecone   — fully managed, serverless, production-ready
  Weaviate   — open-source, multi-modal, GraphQL API
  ChromaDB   — lightweight, Python-native, local-first
  Qdrant     — Rust-based, open-source, high performance
  FAISS      — Facebook library, in-memory, no persistence

Indexing Algorithms
-------------------
HNSW (Hierarchical Navigable Small World): Graph-based, best recall/speed trade-off.
IVF (Inverted File Index): Cluster-based; fast retrieval.
PQ (Product Quantisation): Compresses vectors for memory efficiency.

Retrieval-Augmented Generation (RAG)
-------------------------------------
1. Chunk documents into passages of 256-512 tokens.
2. Embed each chunk using an embedding model.
3. Store embeddings in a vector database.
4. At query time: embed query, run ANN search, retrieve top-k chunks.
5. Inject retrieved chunks into LLM prompt as context.
6. LLM generates a grounded, factual answer.

Key Metrics
-----------
Recall@K      : fraction of true neighbours found in top-K results
MRR           : Mean Reciprocal Rank
NDCG          : Normalised Discounted Cumulative Gain
Latency p95   : 95th-percentile query response time

Bias and Concept Drift
----------------------
Embedding bias: models trained on biased corpora encode social stereotypes.
Concept drift: domain vocabulary evolves; periodic re-embedding is needed.
Mitigation: debiasing layers, regular fine-tuning, cosine drift monitoring.

Practical Considerations
------------------------
Optimal chunk size: 256-512 tokens with 10-20% overlap between chunks.
Re-ranking: Use a cross-encoder after ANN retrieval for precision boost.
Cost estimate: ~$0.02 per 1M tokens with OpenAI ada-002.
"""

source_text = st.text_area(
    "📄 Source Document  (paste text here or upload files in the sidebar)",
    value=default_source,
    height=220,
    label_visibility="visible",
)

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE DIAGRAM (always visible, states update during run)
# ─────────────────────────────────────────────────────────────────────────────
pipeline_placeholder = st.empty()
pipeline_placeholder.markdown(
    _pipeline_html(st.session_state.agent_states),
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# RUN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
if generate_btn:
    # Validate
    if not api_key.strip():
        st.error("⚠️  Please enter your Groq API key in the sidebar.")
        st.stop()

    source = _load_source(uploaded_files, source_text)
    if not source.strip():
        st.error("⚠️  No source content. Paste text or upload a file.")
        st.stop()

    # Reset state
    st.session_state.update({
        "artifacts":     None,
        "iter_log":      [],
        "pdf_bytes":     {},
        "running":       True,
        "log_messages":  [],
        "agent_states":  {"source": "done"},
        "total_seconds": 0,
        "error":         None,
    })

    cfg = GenerationConfig(
        topic_title       = topic_title,
        topic_description = topic_desc,
        learner_profile   = PROFILE_LABELS.get(profile_str, LearnerProfile.MSC_STUDENT),
        pass_threshold    = pass_threshold / 100.0,
        max_retries       = max_retries,
    )

    # ── Live progress area ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚙️ Running Pipeline")
    log_placeholder = st.empty()

    t_start = time.time()

    def progress_cb(msg: str):
        st.session_state.log_messages.append(msg)
        _update_agent_states(st.session_state.agent_states, msg)
        pipeline_placeholder.markdown(
            _pipeline_html(st.session_state.agent_states),
            unsafe_allow_html=True,
        )
        log_placeholder.markdown(
            _log_html(st.session_state.log_messages),
            unsafe_allow_html=True,
        )

    try:
        controller = LessonController(api_key=api_key.strip(), cfg=cfg)
        artifacts, iter_log = controller.run(source, progress_cb=progress_cb)

        st.session_state.artifacts     = artifacts
        st.session_state.iter_log      = iter_log
        st.session_state.total_seconds = round(time.time() - t_start)

        with st.spinner("📄 Generating PDFs …"):
            st.session_state.pdf_bytes = artifacts_to_pdf_bytes(artifacts, cfg)

        st.session_state.running = False
        st.rerun()

    except Exception as exc:
        import traceback
        st.session_state.error   = traceback.format_exc()
        st.session_state.running = False
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ERROR STATE
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error("❌ Pipeline error")
    with st.expander("Show traceback"):
        st.code(st.session_state.error, language="python")


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.artifacts and not st.session_state.running:
    artifacts: LessonArtifacts = st.session_state.artifacts
    iter_log  = st.session_state.iter_log
    pdf_bytes = st.session_state.pdf_bytes

    last      = iter_log[-1] if iter_log else {}
    score_pct = last.get("score_pct", 0)
    passed    = last.get("passed", False)

    st.markdown("---")

    # ── Metric row ───────────────────────────────────────────────────────────
    score_cls = "pass" if passed else "fail"
    st.markdown(
        f"""<div class="metric-row">
  <div class="metric-card {score_cls}">
    <span class="value">{score_pct:.0f}%</span>
    <span class="label">Student Score</span>
  </div>
  <div class="metric-card {'pass' if passed else 'fail'}">
    <span class="value">{"PASS ✓" if passed else "FAIL ✗"}</span>
    <span class="label">Quality Gate</span>
  </div>
  <div class="metric-card info">
    <span class="value">{len(iter_log)}</span>
    <span class="label">Attempt{'s' if len(iter_log) > 1 else ''}</span>
  </div>
  <div class="metric-card warn">
    <span class="value">{st.session_state.total_seconds}s</span>
    <span class="label">Total Time</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_lp, tab_sh, tab_qz, tab_ak, tab_arch, tab_log = st.tabs([
        "📘 Lesson Plan",
        "📋 Student Handout",
        "❓ Quiz",
        "🔑 Answer Key",
        "🏗️ Blueprint",
        "📊 Iteration Log",
    ])

    _ARTEFACTS = [
        (tab_lp,   "lesson_plan",        "Lesson Plan",        artifacts.lesson_plan),
        (tab_sh,   "student_handout",    "Student Handout",    artifacts.student_handout),
        (tab_qz,   "quiz",               "Quiz",               artifacts.quiz),
        (tab_ak,   "teacher_answer_key", "Teacher Answer Key", artifacts.teacher_answer_key),
    ]

    for tab, key, label, content in _ARTEFACTS:
        with tab:
            col_text, col_dl = st.columns([5, 1])
            with col_text:
                st.markdown(content, unsafe_allow_html=False)
            with col_dl:
                if key in pdf_bytes:
                    st.download_button(
                        label="⬇️ PDF",
                        data=pdf_bytes[key],
                        file_name=f"{key}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_{key}",
                    )

    with tab_arch:
        st.code(artifacts.architect_outline, language="json")

    with tab_log:
        for e in iter_log:
            badge_cls = "pass" if e["passed"] else "fail"
            icon      = "✅" if e["passed"] else "❌"
            st.markdown(
                f'<div class="attempt-badge {badge_cls}" style="margin-bottom:.5rem;">'
                f'{icon} Attempt {e["attempt"]} — Score {e["score_pct"]}% — '
                f'{e["total_seconds"]}s</div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Attempt {e['attempt']} — Feedback"):
                st.text(e.get("feedback", ""))

    # ── Download all PDFs ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="dl-section">'
        '<div class="dl-title">⬇️ Download All PDFs</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    dl_cols = st.columns(4)
    dl_labels = [
        ("lesson_plan",        "📘 Lesson Plan"),
        ("student_handout",    "📋 Handout"),
        ("quiz",               "❓ Quiz"),
        ("teacher_answer_key", "🔑 Answer Key"),
    ]
    for col, (key, label) in zip(dl_cols, dl_labels):
        with col:
            if key in pdf_bytes:
                col.download_button(
                    label=label,
                    data=pdf_bytes[key],
                    file_name=f"{key}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_bottom_{key}",
                )

# ─────────────────────────────────────────────────────────────────────────────
# IDLE STATE — How it works cards
# ─────────────────────────────────────────────────────────────────────────────
elif not st.session_state.running and not st.session_state.error:
    st.markdown("---")
    st.markdown("### How It Works")
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "01", "Architect Agent",
         "Analyses raw documentation and maps it to Gagne's 9 Events & "
         "Merrill's First Principles to create a structured blueprint."),
        (c2, "02", "Content Agent",
         "Generates a Lesson Plan, Student Handout, Quiz, and Teacher "
         "Answer Key grounded in the source material and blueprint."),
        (c3, "03", "Simulated Student",
         "Attempts the quiz using only the Student Handout. Produces "
         "a structured failure analysis if below the pass threshold."),
        (c4, "04", "Revision Loop",
         "If the student fails, feedback feeds back to the Architect "
         "to rewrite confusing sections — up to your chosen retry limit."),
    ]
    for col, num, title, desc in cards:
        with col:
            st.markdown(
                f'<div class="how-card">'
                f'<div class="num">{num}</div>'
                f'<div class="ttl">{title}</div>'
                f'<div class="desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="info-banner" style="margin-top:1.2rem;">'
        '💡 <b>Quick start:</b> Paste your documentation in the text area above, '
        'configure the topic and learner profile in the sidebar, '
        'then click <b>🚀 Generate Lesson</b>.'
        '</div>',
        unsafe_allow_html=True,
    )
