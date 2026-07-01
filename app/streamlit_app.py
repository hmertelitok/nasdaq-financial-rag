import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rag_assistant import (
    SUPPORTED_COMPANIES,
    answer_all_companies,
    answer_question,
    get_default_query,
)


st.set_page_config(
    page_title="NASDAQ Financial RAG Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .app-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .app-subtitle {
            font-size: 1rem;
            color: #a0a8b8;
            margin-bottom: 1.25rem;
        }

        .disclaimer {
            border: 1px solid #5f4b1b;
            border-radius: 12px;
            padding: 0.9rem;
            background-color: #1f1a0d;
            color: #facc15;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .small-muted {
            color: #9ca3af;
            font-size: 0.9rem;
            padding-top: 0.55rem;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.45rem;
        }

        div[data-testid="stExpander"] {
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    if "last_results" not in st.session_state:
        st.session_state.last_results = None

    if "last_mode" not in st.session_state:
        st.session_state.last_mode = None

    if "last_company" not in st.session_state:
        st.session_state.last_company = None


def render_header() -> None:
    st.markdown(
        """
        <div class="app-title">NASDAQ Financial RAG Assistant</div>
        <div class="app-subtitle">
        Microsoft Foundry Local ile çalışan, SEC 10-K raporlarına dayalı yerel finansal RAG araştırma asistanı.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> Dict[str, Any]:
    st.sidebar.title("Ayarlar")

    selected_company = st.sidebar.selectbox(
        "Şirket seç",
        options=["ALL"] + list(SUPPORTED_COMPANIES.keys()),
        format_func=lambda ticker: (
            "Tüm şirketler"
            if ticker == "ALL"
            else f"{ticker} - {SUPPORTED_COMPANIES[ticker]}"
        ),
    )

    top_k = st.sidebar.slider(
        "Kaynak sayısı",
        min_value=3,
        max_value=8,
        value=5,
        step=1,
    )

    use_foundry_local = st.sidebar.toggle(
        "Foundry Local LLM kullan",
        value=True,
        help=(
            "Kapalı olursa sistem kaynak tabanlı fallback cevap üretir. "
            "Hızlı UI testi için kullanılabilir."
        ),
    )

    st.sidebar.divider()

    st.sidebar.markdown("### Sistem")
    st.sidebar.markdown("- Retrieval: Semantic Hybrid Rerank")
    st.sidebar.markdown("- LLM: Foundry Local / Qwen2.5-7B")
    st.sidebar.markdown("- Veri: SEC 10-K Reports")
    st.sidebar.markdown("- Dil: Türkçe")

    st.sidebar.divider()

    st.sidebar.markdown(
        """
        <div class="disclaimer">
        Bu uygulama yatırım tavsiyesi vermez. Yalnızca SEC 10-K raporlarına dayalı araştırma amaçlı özetleme yapar.
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "selected_company": selected_company,
        "top_k": top_k,
        "use_foundry_local": use_foundry_local,
    }


def get_company_display_name(ticker: str) -> str:
    if ticker == "ALL":
        return "Tüm şirketler"

    return f"{ticker} - {SUPPORTED_COMPANIES.get(ticker, ticker)}"


def calculate_result_metrics(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sources = result.get("sources", [])

    if not sources:
        return None

    sections = [source.get("section", "Unknown") for source in sources]
    scores = [float(source.get("score", 0)) for source in sources]

    return {
        "source_count": len(sources),
        "avg_score": round(sum(scores) / len(scores), 4),
        "section_diversity": len(set(sections)),
        "top_section": sections[0],
    }


def render_metrics(result: Dict[str, Any]) -> None:
    metrics = calculate_result_metrics(result)

    if metrics is None:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Kaynak Sayısı", metrics["source_count"])

    with col2:
        st.metric("Ortalama Skor", metrics["avg_score"])

    with col3:
        st.metric("Section Çeşitliliği", metrics["section_diversity"])

    with col4:
        st.metric("Top Section", metrics["top_section"])


def render_answer(result: Dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("### RAG Cevabı")
        st.markdown(result.get("answer", "Cevap üretilemedi."))


def render_source(source: Dict[str, Any], index: int) -> None:
    ticker = source.get("ticker", "N/A")
    company_name = source.get("company_name", "N/A")
    filing_type = source.get("filing_type", "N/A")
    filing_date = source.get("filing_date", "N/A")
    section = source.get("section", "N/A")
    raw_section = source.get("raw_section", section)
    chunk_id = source.get("chunk_id", "N/A")
    score = source.get("score", "N/A")
    original_score = source.get("original_score", "N/A")
    retrieval_type = source.get("retrieval_type", "N/A")
    embedding_model = source.get("embedding_model", "N/A")
    source_url = source.get("source_document_url", "")
    excerpt = source.get("excerpt", "")

    expander_title = f"Kaynak {index}: {ticker} | {section} | Skor: {score}"

    with st.expander(expander_title, expanded=index == 1):
        st.markdown(
            f"""
            **Şirket:** {ticker} - {company_name}  
            **Filing:** {filing_type}  
            **Tarih:** {filing_date}  
            **Section:** {section}  
            **Raw Section:** {raw_section}  
            **Chunk ID:** `{chunk_id}`  
            **Hybrid Score:** `{score}`  
            **Semantic Score:** `{original_score}`  
            **Retrieval Type:** `{retrieval_type}`  
            **Embedding Model:** `{embedding_model}`
            """
        )

        if source_url:
            st.link_button("SEC kaynağını aç", source_url)

        if excerpt:
            st.markdown("**Excerpt**")
            st.info(excerpt)


def render_sources(result: Dict[str, Any]) -> None:
    sources = result.get("sources", [])

    if not sources:
        st.warning("Bu cevap için kaynak bulunamadı.")
        return

    st.subheader("Kullanılan Kaynaklar")

    for index, source in enumerate(sources, start=1):
        render_source(source, index)


def render_single_company_result(result: Dict[str, Any]) -> None:
    render_metrics(result)
    st.divider()
    render_answer(result)
    st.divider()
    render_sources(result)


def render_all_company_results(results: List[Dict[str, Any]]) -> None:
    for result in results:
        sources = result.get("sources", [])

        if sources:
            ticker = sources[0].get("ticker", "N/A")
            company_name = sources[0].get("company_name", "N/A")
            title = f"{ticker} - {company_name}"
        else:
            title = "Kaynak bulunamadı"

        st.markdown(f"## {title}")
        render_single_company_result(result)
        st.divider()


def reset_previous_results() -> None:
    st.session_state.last_result = None
    st.session_state.last_results = None
    st.session_state.last_mode = None
    st.session_state.last_company = None


def run_analysis(
    selected_company: str,
    query: str,
    default_query: str,
    top_k: int,
    use_foundry_local: bool,
) -> None:
    reset_previous_results()

    if selected_company == "ALL":
        custom_query = None if query.strip() == default_query else query.strip()

        results = answer_all_companies(
            query=custom_query,
            top_k=top_k,
            use_foundry_local=use_foundry_local,
        )

        st.session_state.last_results = results
        st.session_state.last_mode = "ALL"
        st.session_state.last_company = selected_company
        return

    result = answer_question(
        query=query.strip(),
        ticker=selected_company,
        top_k=top_k,
        use_foundry_local=use_foundry_local,
    )

    st.session_state.last_result = result
    st.session_state.last_mode = "SINGLE"
    st.session_state.last_company = selected_company


def render_saved_results() -> None:
    if st.session_state.last_mode == "ALL" and st.session_state.last_results:
        render_all_company_results(st.session_state.last_results)
        return

    if st.session_state.last_mode == "SINGLE" and st.session_state.last_result:
        render_single_company_result(st.session_state.last_result)
        return

    st.info("Analiz başlatmak için 'Analiz Et' butonuna tıkla.")


def main() -> None:
    apply_custom_style()
    initialize_session_state()
    render_header()

    settings = render_sidebar()

    selected_company = settings["selected_company"]
    top_k = settings["top_k"]
    use_foundry_local = settings["use_foundry_local"]

    ticker_for_default = None if selected_company == "ALL" else selected_company
    default_query = get_default_query(ticker_for_default)

    st.markdown("### Soru")

    query = st.text_area(
        "Analiz etmek istediğin soruyu yaz",
        value=default_query,
        height=120,
        key=f"query_input_{selected_company}",
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        analyze_button = st.button(
            "Analiz Et",
            type="primary",
            use_container_width=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="small-muted">
            Seçilen kapsam: <b>{get_company_display_name(selected_company)}</b> |
            Top-K: <b>{top_k}</b> |
            Foundry Local: <b>{"Açık" if use_foundry_local else "Kapalı"}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if analyze_button:
        if not query.strip():
            st.error("Soru boş olamaz.")
            return

        try:
            with st.spinner(
                "RAG analizi çalışıyor. Foundry Local modeli yükleniyorsa bu işlem biraz sürebilir..."
            ):
                run_analysis(
                    selected_company=selected_company,
                    query=query,
                    default_query=default_query,
                    top_k=top_k,
                    use_foundry_local=use_foundry_local,
                )

        except Exception as error:
            st.error("Analiz sırasında hata oluştu.")
            st.exception(error)
            return

    render_saved_results()


if __name__ == "__main__":
    main()