import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from market_data import get_market_snapshot
from rag_api_client import (
    API_BASE_URL,
    RagApiError,
    SUPPORTED_COMPANIES,
    ask_all_companies,
    ask_company,
    check_api_health,
)


st.set_page_config(
    page_title="NASDAQ Financial RAG Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


ExampleQuestion = Tuple[str, str]


EXAMPLE_QUESTIONS: Dict[str, List[ExampleQuestion]] = {
    "AAPL": [
        (
            "Tedarik zinciri riskleri",
            "Apple'ın tedarik zinciri ve üretim riskleri nelerdir?",
        ),
        (
            "Yapay zekâ riskleri",
            "Apple'ın yapay zekâ ve ürün güvenilirliği riskleri nelerdir?",
        ),
        (
            "Düzenleyici riskler",
            "Apple'ın düzenleyici uyum ve veri gizliliği riskleri nelerdir?",
        ),
    ],
    "MSFT": [
        (
            "Yapay zekâ ve bulut",
            "Microsoft'un yapay zekâ, bulut ve siber güvenlik riskleri nelerdir?",
        ),
        (
            "Veri merkezi riskleri",
            "Microsoft'un veri merkezi kapasitesi ve hizmet sürekliliği riskleri nelerdir?",
        ),
        (
            "Rekabet ve düzenleme",
            "Microsoft'un düzenleyici uyum ve rekabet riskleri nelerdir?",
        ),
    ],
    "NVDA": [
        (
            "İhracat kontrolleri",
            "NVIDIA'nın ihracat kontrolleri ve ülke kısıtlamalarıyla ilgili riskleri nelerdir?",
        ),
        (
            "Tedarik zinciri",
            "NVIDIA'nın tedarik zinciri ve üretim kapasitesi riskleri nelerdir?",
        ),
        (
            "AI talebi ve rekabet",
            "NVIDIA'nın yapay zekâ talebi ve rekabet riskleri nelerdir?",
        ),
    ],
    "AMZN": [
        (
            "AWS riskleri",
            "Amazon'un AWS ve veri merkezi kapasitesiyle ilgili riskleri nelerdir?",
        ),
        (
            "Lojistik riskleri",
            "Amazon'un lojistik ve operasyonel maliyet riskleri nelerdir?",
        ),
        (
            "Düzenleyici riskler",
            "Amazon'un düzenleyici uyum ve rekabet riskleri nelerdir?",
        ),
    ],
    "GOOGL": [
        (
            "Yapay zekâ riskleri",
            "Alphabet'in yapay zekâ ve ürün güvenilirliği riskleri nelerdir?",
        ),
        (
            "Reklam ve rekabet",
            "Alphabet'in reklam faaliyetleri ve rekabet riskleri nelerdir?",
        ),
        (
            "Gizlilik ve düzenleme",
            "Alphabet'in veri gizliliği ve düzenleyici riskleri nelerdir?",
        ),
    ],
    "ALL": [
        (
            "AI risklerini karşılaştır",
            "Seçili şirketlerin yapay zekâ stratejilerini ve risklerini karşılaştır.",
        ),
        (
            "Siber riskleri karşılaştır",
            "Seçili şirketlerin siber güvenlik ve veri gizliliği risklerini karşılaştır.",
        ),
        (
            "Operasyonel riskleri karşılaştır",
            "Seçili şirketlerin tedarik zinciri, veri merkezi ve operasyonel risklerini karşılaştır.",
        ),
    ],
}


def apply_custom_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-primary: #06101e;
            --bg-secondary: #09182a;
            --card-bg: rgba(13, 29, 51, 0.94);
            --card-bg-soft: rgba(17, 37, 64, 0.78);
            --border: rgba(126, 177, 255, 0.16);
            --border-strong: rgba(83, 160, 255, 0.38);
            --text-primary: #f2f7ff;
            --text-secondary: #b8c9e0;
            --text-muted: #8ca2bf;
            --accent: #54a6ff;
            --accent-soft: rgba(84, 166, 255, 0.13);
            --success: #42d392;
            --danger: #ff7f87;
        }

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background:
                radial-gradient(
                    circle at 82% 3%,
                    rgba(28, 108, 218, 0.18),
                    transparent 34%
                ),
                linear-gradient(
                    180deg,
                    var(--bg-primary) 0%,
                    var(--bg-secondary) 100%
                ) !important;
            color: var(--text-primary) !important;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
        }

        #MainMenu,
        footer,
        [data-testid="stAppDeployButton"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* Sidebar aç/kapat düğmesi her zaman görünür kalsın. */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button {
            color: #eaf3ff !important;
            background: rgba(13, 29, 51, 0.92) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 1.15rem;
            padding-bottom: 2.5rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(
                    180deg,
                    rgba(6, 16, 30, 0.99),
                    rgba(9, 27, 48, 0.99)
                ) !important;
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.2rem;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] span {
            color: #bacbe1 !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--text-primary) !important;
        }

        .sidebar-brand {
            padding: 0.1rem 0 0.85rem 0;
        }

        .sidebar-brand-title {
            color: var(--text-primary);
            font-size: 1.18rem;
            font-weight: 800;
        }

        .sidebar-brand-subtitle {
            color: var(--text-muted);
            font-size: 0.80rem;
            margin-top: 0.16rem;
        }

        .sidebar-status {
            margin-top: 0.3rem;
            padding: 0.68rem 0.76rem;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(15, 34, 59, 0.82);
            color: var(--text-secondary);
            font-size: 0.80rem;
            line-height: 1.6;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #0d1d33 !important;
            border-color: rgba(84, 166, 255, 0.30) !important;
            color: #f2f7ff !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] input {
            color: #f2f7ff !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] svg {
            fill: #bacbe1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] {
            overflow: hidden;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            background: rgba(12, 28, 49, 0.80) !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] summary {
            background: #0d1d33 !important;
            color: #f2f7ff !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] summary p {
            color: #f2f7ff !important;
            font-weight: 650 !important;
        }

        .hero-card {
            position: relative;
            overflow: hidden;
            padding: 1.55rem 1.65rem;
            margin-bottom: 0.9rem;
            border: 1px solid var(--border-strong);
            border-radius: 22px;
            background:
                linear-gradient(
                    135deg,
                    rgba(16, 43, 78, 0.97),
                    rgba(8, 25, 47, 0.95)
                );
            box-shadow:
                0 18px 55px rgba(0, 0, 0, 0.27),
                inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .hero-card::after {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: -95px;
            top: -125px;
            border-radius: 50%;
            background: rgba(73, 153, 255, 0.15);
        }

        .hero-kicker {
            position: relative;
            z-index: 1;
            color: #91c8ff;
            font-size: 0.80rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.52rem;
        }

        .hero-title {
            position: relative;
            z-index: 1;
            color: var(--text-primary);
            font-size: clamp(1.85rem, 4vw, 2.55rem);
            line-height: 1.08;
            font-weight: 820;
            margin: 0 0 0.55rem 0;
        }

        .hero-subtitle {
            position: relative;
            z-index: 1;
            max-width: 860px;
            color: var(--text-secondary);
            font-size: 0.98rem;
            line-height: 1.62;
            margin-bottom: 1rem;
        }

        .badge-row {
            position: relative;
            z-index: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 0.52rem;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.34rem;
            padding: 0.40rem 0.70rem;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--accent-soft);
            color: #dceaff;
            font-size: 0.80rem;
            font-weight: 650;
        }

        .badge-success {
            border-color: rgba(66, 211, 146, 0.32);
            background: rgba(66, 211, 146, 0.12);
            color: #a7f3d0;
        }

        .badge-error {
            border-color: rgba(255, 127, 135, 0.34);
            background: rgba(255, 127, 135, 0.12);
            color: #ffc6ca;
        }

        .pipeline-strip {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.44rem;
            margin: 0.30rem 0 0.95rem 0;
            padding: 0.72rem 0.90rem;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(9, 23, 42, 0.76);
            color: var(--text-secondary);
            font-size: 0.84rem;
        }

        .pipeline-node {
            color: #dceaff;
            font-weight: 650;
        }

        .pipeline-arrow {
            color: var(--accent);
            font-weight: 800;
        }

        .section-heading {
            margin: 0 0 0.6rem 0;
            color: var(--text-primary);
            font-size: 1.16rem;
            font-weight: 760;
        }

        .section-caption {
            margin: -0.28rem 0 0.80rem 0;
            color: var(--text-muted);
            font-size: 0.88rem;
            line-height: 1.48;
        }

        .coverage-card {
            min-height: 128px;
            padding: 0.96rem;
            border: 1px solid var(--border);
            border-radius: 16px;
            background:
                linear-gradient(
                    145deg,
                    rgba(16, 37, 64, 0.93),
                    rgba(9, 24, 44, 0.95)
                );
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }

        .coverage-ticker {
            color: var(--text-primary);
            font-size: 1.38rem;
            font-weight: 800;
            margin-bottom: 0.16rem;
        }

        .coverage-company {
            min-height: 40px;
            color: var(--text-secondary);
            font-size: 0.86rem;
            margin-bottom: 0.58rem;
        }

        .coverage-tag {
            display: inline-block;
            padding: 0.20rem 0.52rem;
            border: 1px solid rgba(84, 166, 255, 0.30);
            border-radius: 999px;
            background: rgba(84, 166, 255, 0.10);
            color: #a9d2ff;
            font-size: 0.72rem;
            font-weight: 650;
        }

        div[data-testid="stMetric"] {
            min-height: 104px;
            padding: 0.76rem 0.86rem;
            border: 1px solid var(--border);
            border-radius: 15px;
            background: var(--card-bg);
            box-shadow: 0 9px 26px rgba(0, 0, 0, 0.13);
        }

        div[data-testid="stMetricLabel"] p {
            color: #96aac5 !important;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-size: 1.30rem;
        }

        .query-shell {
            margin-top: 0.08rem;
            padding: 0.98rem 1.06rem 0.72rem 1.06rem;
            border: 1px solid var(--border);
            border-radius: 17px;
            background: var(--card-bg);
            box-shadow: 0 11px 34px rgba(0, 0, 0, 0.16);
        }

        .query-title {
            color: var(--text-primary);
            font-size: 1.12rem;
            font-weight: 760;
            margin-bottom: 0.26rem;
        }

        .query-caption {
            color: var(--text-muted);
            font-size: 0.86rem;
            line-height: 1.45;
        }

        .example-caption {
            color: var(--text-muted);
            font-size: 0.84rem;
            margin: 0.56rem 0 0.42rem 0;
        }

        div[data-testid="stTextArea"] textarea {
            min-height: 100px;
            border: 1px solid var(--border-strong) !important;
            border-radius: 14px !important;
            background: rgba(7, 19, 35, 0.95) !important;
            color: var(--text-primary) !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextArea"] textarea::placeholder {
            color: #849bb9 !important;
            opacity: 1 !important;
        }

        div[data-testid="stTextArea"] textarea:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px rgba(84, 166, 255, 0.14) !important;
        }

        /* Ana analiz butonu */
        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 42px;
            border: 1px solid rgba(84, 166, 255, 0.45) !important;
            border-radius: 12px !important;
            background:
                linear-gradient(
                    135deg,
                    #2d7fe9,
                    #51a9ff
                ) !important;
            color: #ffffff !important;
            font-weight: 750 !important;
            box-shadow: 0 8px 24px rgba(45, 127, 233, 0.23);
        }

        /* Örnek soru ve diğer ikincil butonlar */
        div[data-testid="stButton"] button[kind="secondary"] {
            min-height: 38px;
            border: 1px solid rgba(84, 166, 255, 0.28) !important;
            border-radius: 11px !important;
            background: rgba(13, 31, 55, 0.94) !important;
            color: #dbeaff !important;
            font-weight: 650 !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover {
            border-color: rgba(84, 166, 255, 0.62) !important;
            background: rgba(20, 48, 83, 0.98) !important;
            color: #ffffff !important;
        }

        .analysis-context {
            display: flex;
            align-items: center;
            min-height: 100%;
            color: var(--text-muted);
            font-size: 0.84rem;
            padding-top: 0.42rem;
        }

        .analysis-context strong {
            color: #dceaff;
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: center;
            margin: 0.55rem 0 0.78rem 0;
            padding: 0.86rem 0.96rem;
            border: 1px solid rgba(66, 211, 146, 0.24);
            border-radius: 15px;
            background: rgba(66, 211, 146, 0.08);
        }

        .result-title {
            color: #d8ffec;
            font-size: 1rem;
            font-weight: 760;
        }

        .result-subtitle {
            color: #9fcdb8;
            font-size: 0.80rem;
            margin-top: 0.16rem;
        }

        .answer-label {
            color: #9dcaff;
            font-size: 0.77rem;
            font-weight: 760;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.34rem;
        }

        /* Sonuç ve cevap container'ları */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--border-strong) !important;
            border-radius: 17px !important;
            background:
                linear-gradient(
                    145deg,
                    rgba(15, 34, 59, 0.94),
                    rgba(8, 22, 41, 0.96)
                ) !important;
        }

        .source-section-title {
            color: var(--text-primary);
            font-size: 1.10rem;
            font-weight: 760;
            margin: 0.92rem 0 0.52rem 0;
        }

        .source-summary {
            color: var(--text-muted);
            font-size: 0.84rem;
            margin-bottom: 0.6rem;
        }

        div[data-testid="stExpander"] {
            overflow: hidden;
            margin-bottom: 0.55rem;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            background: rgba(11, 27, 48, 0.86) !important;
        }

        div[data-testid="stExpander"] summary {
            background: rgba(14, 32, 56, 0.98) !important;
            color: #e7f1ff !important;
        }

        div[data-testid="stExpander"] summary p {
            color: #e7f1ff !important;
            font-weight: 650 !important;
        }

        div[data-testid="stExpander"] summary svg {
            fill: #a9cfff !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 13px;
        }

        hr {
            border-color: rgba(255, 255, 255, 0.06) !important;
            margin-top: 1rem !important;
            margin-bottom: 1rem !important;
        }

        @media (max-width: 780px) {
            .hero-card {
                padding: 1.25rem;
            }

            .hero-title {
                font-size: 1.82rem;
            }

            .coverage-card {
                min-height: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=15, show_spinner=False)
def load_api_health() -> Dict[str, Any]:
    return check_api_health()


@st.cache_data(ttl=900, show_spinner=False)
def load_market_snapshot(ticker: str) -> Dict[str, Any]:
    return get_market_snapshot(ticker)


def initialize_session_state() -> None:
    defaults = {
        "last_result": None,
        "last_results": None,
        "last_mode": None,
        "last_company": None,
        "active_company": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_saved_results() -> None:
    st.session_state.last_result = None
    st.session_state.last_results = None
    st.session_state.last_mode = None
    st.session_state.last_company = None


def get_friendly_api_error(error: Any) -> str:
    error_text = str(error or "")
    normalized = error_text.lower()

    connection_terms = (
        "winerror 10061",
        "connection refused",
        "max retries exceeded",
        "failed to establish a new connection",
        "bağlantı kurulamadı",
    )

    if any(term in normalized for term in connection_terms):
        return (
            "RAG API servisine ulaşılamadı. "
            "ASP.NET Core ve FastAPI servislerinin çalıştığını kontrol edin."
        )

    if (
        "timeout" in normalized
        or "timed out" in normalized
        or "zaman aşımı" in normalized
    ):
        return (
            "API isteği zaman aşımına uğradı. "
            "Model hazırlanıyor olabilir; kısa süre sonra tekrar deneyin."
        )

    server_terms = (
        "http 500",
        "http 502",
        "status: 500",
        "status: 502",
        "tensorrt",
        "server_error",
    )

    if any(term in normalized for term in server_terms):
        return (
            "Yapay zekâ servisi geçici olarak yanıt üretemedi. "
            "FastAPI veya Foundry Local servisini yeniden başlatıp tekrar deneyin."
        )

    return (
        "API bağlantısı sırasında beklenmeyen bir hata oluştu. "
        "Servis durumlarını kontrol edip tekrar deneyin."
    )


def get_api_status() -> Dict[str, Any]:
    try:
        health = load_api_health()

        return {
            "healthy": health.get("status") == "healthy",
            "health": health,
            "error": None,
        }
    except RagApiError as error:
        return {
            "healthy": False,
            "health": None,
            "error": str(error),
        }


def render_hero(api_status: Dict[str, Any]) -> None:
    if api_status["healthy"]:
        api_badge_class = "badge badge-success"
        api_badge_text = "● API Aktif"
    else:
        api_badge_class = "badge badge-error"
        api_badge_text = "● API Kapalı"

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">Local AI Financial Research</div>
            <div class="hero-title">NASDAQ Financial RAG Assistant</div>
            <div class="hero-subtitle">
                Seçili NASDAQ şirketlerinin SEC 10-K raporlarını
                PostgreSQL + pgvector ile tarayan, Microsoft Foundry Local
                üzerinden kaynak temelli Türkçe cevaplar üreten finansal
                araştırma asistanı.
            </div>
            <div class="badge-row">
                <span class="{api_badge_class}">{api_badge_text}</span>
                <span class="badge">5 Şirket</span>
                <span class="badge">334 Chunk</span>
                <span class="badge">SEC 10-K</span>
                <span class="badge">Local LLM</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_strip() -> None:
    st.markdown(
        """
        <div class="pipeline-strip">
            <span class="pipeline-node">Streamlit</span>
            <span class="pipeline-arrow">→</span>
            <span class="pipeline-node">ASP.NET Core</span>
            <span class="pipeline-arrow">→</span>
            <span class="pipeline-node">FastAPI</span>
            <span class="pipeline-arrow">→</span>
            <span class="pipeline-node">PostgreSQL + pgvector</span>
            <span class="pipeline-arrow">→</span>
            <span class="pipeline-node">Foundry Local</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(
    api_status: Dict[str, Any],
) -> Dict[str, Any]:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Kontrol Paneli</div>
            <div class="sidebar-brand-subtitle">
                Yerel finansal RAG araştırma arayüzü
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_company = st.sidebar.selectbox(
        "Şirket seç",
        options=["ALL"] + list(SUPPORTED_COMPANIES.keys()),
        index=1,
        format_func=lambda ticker: (
            "Tüm şirketler"
            if ticker == "ALL"
            else f"{ticker} — {SUPPORTED_COMPANIES[ticker]}"
        ),
    )

    top_k = st.sidebar.slider(
        "Kaynak sayısı",
        min_value=3,
        max_value=8,
        value=5,
        step=1,
        help="RAG cevabında kullanılacak en alakalı SEC kaynak sayısı.",
    )

    st.sidebar.divider()
    st.sidebar.markdown("### Sistem Durumu")

    if api_status["healthy"]:
        st.sidebar.success("ASP.NET Core API aktif")
    else:
        friendly_error = get_friendly_api_error(
            api_status.get("error")
        )
        st.sidebar.error(friendly_error)

        if api_status.get("error"):
            with st.sidebar.expander(
                "Hata Detayını Gör",
                expanded=False,
            ):
                st.caption(
                    "Bu bölüm geliştirme ve hata ayıklama amacıyla gösterilir."
                )
                st.code(
                    str(api_status["error"]),
                    language="text",
                )

    st.sidebar.markdown(
        f"""
        <div class="sidebar-status">
            <strong>API:</strong> {API_BASE_URL}<br>
            <strong>Model:</strong> Qwen2.5-7B<br>
            <strong>Embedding:</strong> multilingual-e5-small
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    with st.sidebar.expander(
        "Sistem detayları",
        expanded=False,
    ):
        st.markdown(
            """
            - **Frontend:** Streamlit
            - **Public API:** ASP.NET Core
            - **AI Servisi:** FastAPI
            - **Retrieval:** PostgreSQL + pgvector
            - **LLM:** Microsoft Foundry Local
            - **Veri:** SEC 10-K
            - **Market Data:** yfinance
            - **Dil:** Türkçe
            """
        )

    with st.sidebar.expander(
        "Yasal uyarı",
        expanded=False,
    ):
        st.caption(
            "Bu uygulama yatırım tavsiyesi sunmaz. "
            "Yanıtlar yalnızca SEC 10-K raporlarına dayalı "
            "araştırma ve özetleme amacı taşır."
        )

    return {
        "selected_company": selected_company,
        "top_k": top_k,
    }


def get_company_display_name(ticker: str) -> str:
    if ticker == "ALL":
        return "Tüm şirketler"

    return f"{ticker} — {SUPPORTED_COMPANIES.get(ticker, ticker)}"


def format_money(value: Any, currency: str = "USD") -> str:
    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.2f} {currency}"
    except (TypeError, ValueError):
        return "N/A"


def format_percent(value: Any) -> str:
    if value is None:
        return "N/A"

    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_price_delta(
    change_value: Any,
    change_percent: Any,
    currency: str = "USD",
) -> str:
    try:
        change_float = float(change_value)
        percent_float = float(change_percent)

        return (
            f"{change_float:+.2f} {currency} "
            f"({percent_float:+.2f}%)"
        )
    except (TypeError, ValueError):
        return "N/A"


def render_company_coverage() -> None:
    st.markdown(
        '<div class="section-heading">İncelenen Şirketler</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="section-caption">
            Beş NASDAQ şirketinin SEC 10-K raporları üzerinden
            karşılaştırmalı risk ve faaliyet analizi.
        </div>
        """,
        unsafe_allow_html=True,
    )

    company_cards = list(SUPPORTED_COMPANIES.items())
    columns = st.columns(len(company_cards))

    for column, (ticker, company_name) in zip(
        columns,
        company_cards,
    ):
        with column:
            st.markdown(
                f"""
                <div class="coverage-card">
                    <div class="coverage-ticker">{ticker}</div>
                    <div class="coverage-company">{company_name}</div>
                    <div class="coverage-tag">SEC 10-K</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_market_snapshot(ticker: str) -> None:
    st.markdown(
        '<div class="section-heading">Market Snapshot</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="section-caption">
            Güncel piyasa verileri yalnızca bağlamsal bilgi
            sağlamak amacıyla gösterilir.
        </div>
        """,
        unsafe_allow_html=True,
    )

    snapshot = load_market_snapshot(ticker)

    if not snapshot.get("ok"):
        st.warning(
            f"{ticker} için piyasa verisi alınamadı: "
            f"{snapshot.get('error')}"
        )
        return

    currency = snapshot.get("currency", "USD")
    daily_change = snapshot.get("daily_change")
    daily_change_percent = snapshot.get(
        "daily_change_percent"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Ticker",
            value=snapshot.get("ticker", ticker),
        )

    with col2:
        st.metric(
            label="Last Close",
            value=format_money(
                snapshot.get("last_close"),
                currency,
            ),
        )

    with col3:
        st.metric(
            label="Daily Change",
            value=format_percent(daily_change_percent),
            delta=format_price_delta(
                daily_change,
                daily_change_percent,
                currency,
            ),
        )

    with col4:
        st.metric(
            label="Price Date",
            value=snapshot.get("price_date", "N/A"),
        )

    st.caption(
        "Üretilen yanıtlar SEC 10-K raporlarına dayanır "
        "ve yatırım tavsiyesi niteliği taşımaz."
    )


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def calculate_result_metrics(
    result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    sources = result.get("sources", [])

    if not sources:
        return None

    sections = [
        source.get("section") or "Unknown"
        for source in sources
    ]
    scores = [
        safe_float(source.get("score"))
        for source in sources
    ]

    return {
        "source_count": len(sources),
        "avg_score": round(
            sum(scores) / len(scores),
            4,
        ),
        "section_diversity": len(set(sections)),
        "top_section": sections[0],
    }


def render_result_header(
    selected_company: str,
    result: Dict[str, Any],
) -> None:
    source_count = len(result.get("sources", []))

    st.markdown(
        f"""
        <div class="result-header">
            <div>
                <div class="result-title">Analiz tamamlandı</div>
                <div class="result-subtitle">
                    {get_company_display_name(selected_company)} ·
                    {source_count} SEC kaynağı kullanıldı
                </div>
            </div>
            <span class="badge badge-success">Kaynak Temelli</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(result: Dict[str, Any]) -> None:
    metrics = calculate_result_metrics(result)

    if metrics is None:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Kaynak Sayısı",
            metrics["source_count"],
        )

    with col2:
        st.metric(
            "Ortalama Skor",
            metrics["avg_score"],
        )

    with col3:
        st.metric(
            "Section Çeşitliliği",
            metrics["section_diversity"],
        )

    with col4:
        st.metric(
            "Top Section",
            metrics["top_section"],
        )


def render_answer(result: Dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown(
            '<div class="answer-label">RAG Cevabı</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            result.get("answer") or "Cevap üretilemedi."
        )


def render_source(
    source: Dict[str, Any],
    index: int,
) -> None:
    ticker = source.get("ticker", "N/A")
    company_name = source.get("company_name", "N/A")
    filing_type = source.get("filing_type", "N/A")
    filing_date = source.get("filing_date", "N/A")
    section = source.get("section", "N/A")
    raw_section = source.get("raw_section", section)
    chunk_id = source.get("chunk_id", "N/A")
    score = source.get("score", "N/A")
    retrieval_type = source.get(
        "retrieval_type",
        "N/A",
    )
    embedding_model = source.get(
        "embedding_model",
        "N/A",
    )
    source_url = source.get(
        "source_document_url",
        "",
    )
    excerpt = source.get("excerpt", "")

    expander_title = (
        f"Kaynak {index} · {ticker} · "
        f"{section} · Skor {score}"
    )

    with st.expander(
        expander_title,
        expanded=index == 1,
    ):
        meta_col1, meta_col2, meta_col3 = st.columns(3)

        with meta_col1:
            st.caption("Şirket")
            st.markdown(
                f"**{ticker} — {company_name}**"
            )

        with meta_col2:
            st.caption("Filing")
            st.markdown(
                f"**{filing_type} · {filing_date}**"
            )

        with meta_col3:
            st.caption("Bölüm")
            st.markdown(f"**{section}**")

        st.markdown(
            f"""
            **Raw Section:** {raw_section}  
            **Chunk ID:** `{chunk_id}`  
            **Benzerlik Skoru:** `{score}`  
            **Retrieval Type:** `{retrieval_type}`  
            **Embedding Model:** `{embedding_model}`
            """
        )

        if source_url:
            st.link_button(
                "SEC kaynağını aç",
                source_url,
            )

        if excerpt:
            st.markdown("**Kaynak metin**")
            st.info(excerpt)


def render_sources(result: Dict[str, Any]) -> None:
    sources = result.get("sources", [])

    if not sources:
        st.warning("Bu cevap için kaynak bulunamadı.")
        return

    st.markdown(
        '<div class="source-section-title">'
        'Kullanılan Kaynaklar'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="source-summary">
            Cevap, aşağıdaki {len(sources)} SEC doküman
            parçası üzerinden oluşturuldu.
        </div>
        """,
        unsafe_allow_html=True,
    )

    for index, source in enumerate(
        sources,
        start=1,
    ):
        render_source(source, index)


def render_single_company_result(
    result: Dict[str, Any],
    selected_company: Optional[str] = None,
) -> None:
    ticker = (
        selected_company
        or result.get("ticker")
        or "N/A"
    )

    render_result_header(ticker, result)
    render_metrics(result)
    st.divider()
    render_answer(result)
    st.divider()
    render_sources(result)


def render_all_company_results(
    results: List[Dict[str, Any]],
) -> None:
    for result in results:
        sources = result.get("sources", [])
        ticker = result.get("ticker")

        if sources:
            ticker = sources[0].get("ticker") or ticker
            company_name = (
                sources[0].get("company_name")
                or SUPPORTED_COMPANIES.get(
                    ticker,
                    "N/A",
                )
            )
            title = f"{ticker} — {company_name}"
        elif ticker:
            title = (
                f"{ticker} — "
                f"{SUPPORTED_COMPANIES.get(ticker, ticker)}"
            )
        else:
            title = "Kaynak bulunamadı"

        st.markdown(f"## {title}")
        render_single_company_result(
            result,
            selected_company=ticker,
        )
        st.divider()


def get_query_key(selected_company: str) -> str:
    return f"query_input_{selected_company}"


def get_example_questions(
    selected_company: str,
) -> Sequence[ExampleQuestion]:
    normalized = str(
        selected_company or "ALL"
    ).upper()

    return EXAMPLE_QUESTIONS.get(
        normalized,
        EXAMPLE_QUESTIONS["ALL"],
    )


def set_query_value(
    query_key: str,
    question: str,
) -> None:
    st.session_state[query_key] = question


def render_example_questions(
    selected_company: str,
    query_key: str,
) -> None:
    questions = get_example_questions(
        selected_company
    )

    st.markdown(
        """
        <div class="example-caption">
            Örnek sorulardan birini seçebilir veya kendi sorunuzu yazabilirsiniz.
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(questions))

    for index, (label, question) in enumerate(questions):
        with columns[index]:
            st.button(
                label,
                key=(
                    f"example_question_"
                    f"{selected_company}_{index}"
                ),
                use_container_width=True,
                on_click=set_query_value,
                args=(query_key, question),
            )


def run_analysis(
    selected_company: str,
    query: str,
    top_k: int,
) -> None:
    clear_saved_results()

    normalized_query = query.strip()

    if selected_company == "ALL":
        results = ask_all_companies(
            query=normalized_query,
            top_k=top_k,
        )

        st.session_state.last_results = results
        st.session_state.last_mode = "ALL"
        st.session_state.last_company = (
            selected_company
        )
        return

    result = ask_company(
        query=normalized_query,
        ticker=selected_company,
        top_k=top_k,
    )

    st.session_state.last_result = result
    st.session_state.last_mode = "SINGLE"
    st.session_state.last_company = selected_company


def render_saved_results() -> None:
    if (
        st.session_state.last_mode == "ALL"
        and st.session_state.last_results
    ):
        render_all_company_results(
            st.session_state.last_results
        )
        return

    if (
        st.session_state.last_mode == "SINGLE"
        and st.session_state.last_result
    ):
        render_single_company_result(
            st.session_state.last_result,
            selected_company=(
                st.session_state.last_company
            ),
        )
        return

    st.info(
        "Analiz başlatmak için sorunuzu yazın ve "
        "'Analiz Et' butonuna tıklayın."
    )


def render_query_panel(
    selected_company: str,
    top_k: int,
) -> bool:
    query_key = get_query_key(
        selected_company
    )

    st.markdown(
        """
        <div class="query-shell">
            <div class="query-title">
                Finansal Raporlara Soru Sor
            </div>
            <div class="query-caption">
                Riskler, düzenleyici baskılar, yapay zekâ,
                bulut, rekabet veya tedarik zinciri hakkında
                kendi sorunuzu yazın.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_example_questions(
        selected_company=selected_company,
        query_key=query_key,
    )

    query = st.text_area(
        "Analiz etmek istediğin soruyu yaz",
        placeholder="Sorunuzu buraya yazın...",
        height=100,
        key=query_key,
        label_visibility="collapsed",
    )

    button_col, context_col = st.columns([1, 4])

    with button_col:
        analyze_button = st.button(
            "Analiz Et",
            type="primary",
            use_container_width=True,
        )

    with context_col:
        st.markdown(
            f"""
            <div class="analysis-context">
                Analiz kapsamı:
                <strong>
                    {get_company_display_name(selected_company)}
                </strong>
                &nbsp;·&nbsp;
                Kaynak:
                <strong>{top_k}</strong>
                &nbsp;·&nbsp;
                Veri:
                <strong>SEC 10-K</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not analyze_button:
        return False

    if not query.strip():
        st.warning(
            "Analiz başlatmak için bir soru yazın "
            "veya örnek sorulardan birini seçin."
        )
        return False

    try:
        load_api_health.clear()
        check_api_health()

        with st.spinner(
            "SEC kaynakları taranıyor ve "
            "RAG cevabı hazırlanıyor..."
        ):
            run_analysis(
                selected_company=selected_company,
                query=query,
                top_k=top_k,
            )

        return True

    except RagApiError as error:
        st.error(
            get_friendly_api_error(error)
        )

        with st.expander(
            "Hata Detayını Gör",
            expanded=False,
        ):
            st.code(
                str(error),
                language="text",
            )

        return False

    except Exception as error:
        st.error(
            "Analiz sırasında beklenmeyen bir hata oluştu."
        )

        with st.expander(
            "Hata Detayını Gör",
            expanded=False,
        ):
            st.exception(error)

        return False


def main() -> None:
    apply_custom_style()
    initialize_session_state()

    api_status = get_api_status()
    settings = render_sidebar(api_status)

    selected_company = settings["selected_company"]
    top_k = settings["top_k"]

    if (
        st.session_state.active_company
        != selected_company
    ):
        clear_saved_results()
        st.session_state.active_company = (
            selected_company
        )

    render_hero(api_status)
    render_pipeline_strip()

    if selected_company == "ALL":
        render_company_coverage()
    else:
        render_market_snapshot(selected_company)

    st.divider()

    render_query_panel(
        selected_company=selected_company,
        top_k=top_k,
    )

    st.divider()
    render_saved_results()


if __name__ == "__main__":
    main()
