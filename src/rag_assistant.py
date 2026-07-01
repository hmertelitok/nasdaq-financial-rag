import atexit
import re
from typing import Any, Dict, List, Optional, Tuple

import openai
from foundry_local_sdk import Configuration, FoundryLocalManager

from retriever import search_relevant_chunks


DEFAULT_MODEL_ALIAS = "qwen2.5-7b"
CONTEXT_CHUNK_CHAR_LIMIT = 1000
DEBUG_CONTEXT = False

_FOUNDRY_MANAGER: Optional[Any] = None
_FOUNDRY_MODEL: Optional[Any] = None
_FOUNDRY_CLIENT: Optional[openai.OpenAI] = None
_FOUNDRY_MODEL_ALIAS: Optional[str] = None

SUPPORTED_COMPANIES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}

SYSTEM_MESSAGE = (
    "Sen SEC 10-K raporlarına dayalı çalışan bir finansal araştırma asistanısın. "
    "Sadece verilen kaynak metinlere dayanarak cevap ver. "
    "Kaynaklarda olmayan bilgiyi uydurma. "
    "Cevabı tamamen Türkçe yaz. "
    "Yatırım tavsiyesi verme. "
    "Kısa, net ve madde madde cevap ver."
)


def normalize_output_text(text: str) -> str:
    replacements = {
        "bağlantılıriskler": "bağlantılı riskler",
        "Tarim": "Tarifeler",
        "tarim": "tarifeler",
        "yatırım tavsiyes\n": "yatırım tavsiyesi değildir.\n",
        "olumlu veya olumsuz etki": "olumsuz etki",
        "olumlu ya da olumsuz etki": "olumsuz etki",
        "Apple'nın": "Apple’ın",
        "Apple'in": "Apple’ın",
        "Microsoft'un": "Microsoft’un",
        "NVIDIA'nın": "NVIDIA’nın",
        "Amazon'un": "Amazon’un",
        "Alphabet'in": "Alphabet’in",
        "veri gizlilik": "veri gizliliği",
        "tedarik hizmetleri": "tedarik süreçleri",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return text


def trim_text(text: str, max_chars: int = CONTEXT_CHUNK_CHAR_LIMIT) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[:max_chars].strip() + "..."


def build_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    context_blocks = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        block = (
            f"Kaynak {index}\n"
            f"Şirket: {chunk.get('ticker')} - {chunk.get('company_name')}\n"
            f"Filing: {chunk.get('filing_type')}\n"
            f"Section: {chunk.get('section')}\n"
            f"Chunk ID: {chunk.get('chunk_id')}\n"
            f"Benzerlik Skoru: {chunk.get('score')}\n"
            f"Metin: {trim_text(chunk.get('text', ''))}"
        )
        context_blocks.append(block)

    return "\n\n".join(context_blocks)


def build_user_prompt(query: str, context: str) -> str:
    return (
        f"Kullanıcı sorusu:\n{query}\n\n"
        f"SEC 10-K kaynak metinleri:\n{context}\n\n"
        "Görev:\n"
        "Aşağıdaki kaynaklara dayanarak tamamen Türkçe, kısa ve kaynaklı bir cevap üret.\n"
        "Cevap sadece riskleri ve olası olumsuz etkileri açıklamalıdır.\n"
        "Her önemli kaynaktan risk çıkarımı yapmaya çalış.\n\n"
        "Mutlaka kontrol edilecek risk kategorileri:\n"
        "- Yapay zeka, bulut, veri merkezi veya teknoloji dönüşümü\n"
        "- Veri gizliliği, güvenlik ve regülasyon\n"
        "- Tedarik zinciri, satın alma taahhütleri ve arz-talep dengesi\n"
        "- Makroekonomik koşullar ve operasyonel maliyetler\n"
        "- Ülke bazlı kısıtlamalar, ihracat kontrolleri veya rekabet baskısı\n\n"
        "Cevap formatı:\n"
        "1. Kısa cevap: 1-2 cümle.\n"
        "2. Öne çıkan riskler: En fazla 4 madde.\n"
        "3. Kullanılan kaynaklar: Kaynak numaralarını yaz.\n"
        "4. Uyarı: Bu çıktı yatırım tavsiyesi değildir.\n\n"
        "Kurallar:\n"
        "- Kaynaklarda olmayan bilgiyi ekleme.\n"
        "- İngilizce kaynak metinleri Türkçeye çevirerek özetle.\n"
        "- Düşünme süreci, analiz notu veya <think> bloğu yazma.\n"
        "- Aynı cümleyi tekrar etme.\n"
        "- 'Olumlu veya olumsuz etki' gibi belirsiz ifadeler kullanma.\n"
        "- Riskleri 'olumsuz etkileyebilir', 'baskı oluşturabilir', 'maliyetleri artırabilir' gibi net ifadelerle açıkla."
    )


def clean_answer(answer: str) -> str:
    answer = answer.strip()
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.IGNORECASE | re.DOTALL)
    answer = answer.replace("<think>", "").replace("</think>", "").strip()

    lines = answer.splitlines()
    cleaned_lines = []
    seen_lines = set()

    for line in lines:
        normalized = " ".join(line.strip().split())

        if not normalized:
            cleaned_lines.append("")
            continue

        if normalized in seen_lines:
            continue

        seen_lines.add(normalized)
        cleaned_lines.append(line.strip())

    cleaned_answer = "\n".join(cleaned_lines).strip()

    if len(cleaned_answer) > 1600:
        cleaned_answer = cleaned_answer[:1600].strip() + "..."

    return normalize_output_text(cleaned_answer)


def is_invalid_answer(answer: str) -> bool:
    lower_answer = answer.lower()

    invalid_terms = [
        "<think>",
        "okay, the user",
        "first, i need",
        "looking at source",
        "the user is asking",
        "i should",
        "kaynaklarda olmayan bilgiyi ekleme",
        "düşünme süreci",
        "en fazla 3 madde",
        "cevap formatı",
        "kurallar:",
        "aynı cümleyi tekrar etme",
        "olumlu veya olumsuz",
        "olumlu ya da olumsuz",
        "olumlu etki",
        "olumlu etkiler",
        "etki verebilir",
        "geleksi",
        "tarim",
        "yatırım tavsiyes",
        "bağlantılıriskler",
        "apple'nın",
        "veri gizlilik",
    ]

    if any(term in lower_answer for term in invalid_terms):
        return True

    required_sections = [
        "1. kısa cevap",
        "2. öne çıkan riskler",
        "3. kullanılan kaynaklar",
        "4. uyarı",
    ]

    if any(section not in lower_answer for section in required_sections):
        return True

    if "yatırım tavsiyesi değildir" not in lower_answer:
        return True

    if "kaynak 1, kaynak 1" in lower_answer:
        return True

    if "kullanılan kaynaklar: 1, 1" in lower_answer:
        return True

    if "kullanılan kaynaklar: kaynak 1, kaynak 1" in lower_answer:
        return True

    sentences = [sentence.strip() for sentence in answer.split(".") if sentence.strip()]
    unique_sentences = set(sentences)

    if len(sentences) >= 6 and len(unique_sentences) <= 3:
        return True

    if len(answer.strip()) < 40:
        return True

    return False


def add_unique_risk(
    risk_items: List[str],
    condition: bool,
    risk_text: str,
) -> None:
    if condition and risk_text not in risk_items:
        risk_items.append(risk_text)


def build_company_specific_risk_items(ticker: str, full_text: str) -> List[str]:
    risk_items = []

    if ticker == "AAPL":
        add_unique_risk(
            risk_items,
            "iphone" in full_text
            or "ipad" in full_text
            or "mac" in full_text
            or "wearables" in full_text
            or "services" in full_text
            or "product" in full_text,
            "Ürün talebi, yeni ürün döngüleri ve hizmet gelirlerindeki değişimler Apple’ın gelir büyümesi ve kâr marjları üzerinde baskı oluşturabilir.",
        )

        add_unique_risk(
            risk_items,
            "supply" in full_text
            or "supplier" in full_text
            or "manufacturing" in full_text
            or "china" in full_text
            or "inventory" in full_text,
            "Tedarik zinciri, üretim ortakları, stok yönetimi ve Çin merkezli operasyonel bağımlılıklar ürün bulunabilirliğini ve maliyetleri olumsuz etkileyebilir.",
        )

        add_unique_risk(
            risk_items,
            "app store" in full_text
            or "regulation" in full_text
            or "regulatory" in full_text
            or "privacy" in full_text
            or "digital markets" in full_text
            or "antitrust" in full_text,
            "App Store, veri gizliliği, dijital pazar düzenlemeleri ve rekabet hukuku kaynaklı regülasyonlar Apple’ın hizmet gelirleri ve iş modeli üzerinde baskı yaratabilir.",
        )

        add_unique_risk(
            risk_items,
            "competition" in full_text
            or "competitive" in full_text
            or "market" in full_text,
            "Akıllı telefon, bilgisayar, giyilebilir cihaz ve dijital hizmet pazarlarındaki yoğun rekabet fiyatlama gücünü ve pazar payını olumsuz etkileyebilir.",
        )

    elif ticker == "MSFT":
        add_unique_risk(
            risk_items,
            "cloud" in full_text
            or "azure" in full_text
            or "data center" in full_text
            or "datacenter" in full_text
            or "artificial intelligence" in full_text
            or "ai" in full_text,
            "Azure, yapay zeka ve veri merkezi ölçeğindeki büyüme yüksek altyapı yatırımı, kapasite planlaması ve operasyonel maliyet baskısı oluşturabilir.",
        )

        add_unique_risk(
            risk_items,
            "cybersecurity" in full_text
            or "security" in full_text
            or "privacy" in full_text
            or "data" in full_text,
            "Siber güvenlik, veri gizliliği ve müşteri verilerinin korunmasına ilişkin riskler itibar, müşteri güveni ve yasal sorumluluklar üzerinde olumsuz etki yaratabilir.",
        )

        add_unique_risk(
            risk_items,
            "regulation" in full_text
            or "regulatory" in full_text
            or "antitrust" in full_text
            or "legal proceedings" in full_text
            or "compliance" in full_text,
            "Yapay zeka, bulut hizmetleri, veri kullanımı ve rekabet hukuku alanındaki düzenleyici denetimler Microsoft’un ürün stratejisini ve faaliyet sonuçlarını etkileyebilir.",
        )

        add_unique_risk(
            risk_items,
            "competition" in full_text
            or "competitive" in full_text
            or "competitors" in full_text,
            "Bulut, üretken yapay zeka, işletim sistemleri, oyun ve verimlilik yazılımlarındaki yoğun rekabet büyüme beklentilerini ve marjları baskılayabilir.",
        )

    elif ticker == "NVDA":
        add_unique_risk(
            risk_items,
            "artificial intelligence" in full_text
            or "accelerated computing" in full_text
            or "data center" in full_text
            or "datacenter" in full_text
            or "gpu" in full_text
            or "blackwell" in full_text,
            "Yapay zeka ve veri merkezi talebindeki hızlı büyüme NVIDIA için yüksek üretim kapasitesi, teknoloji geçişleri ve müşteri beklentileri açısından operasyonel baskı oluşturabilir.",
        )

        add_unique_risk(
            risk_items,
            "export controls" in full_text
            or "china" in full_text
            or "restrictions" in full_text
            or "chinese government" in full_text,
            "İhracat kontrolleri, Çin pazarı ve ülke bazlı düzenleyici kısıtlamalar NVIDIA’nın veri merkezi gelirlerini ve uluslararası rekabet gücünü baskılayabilir.",
        )

        add_unique_risk(
            risk_items,
            "supply" in full_text
            or "supplier" in full_text
            or "purchase obligations" in full_text
            or "non-cancellable" in full_text
            or "non-returnable" in full_text,
            "Tedarik zinciri, iptal edilemeyen satın alma taahhütleri ve arz-talep tahminlerindeki sapmalar maliyetleri, gelir zamanlamasını ve brüt kâr marjlarını olumsuz etkileyebilir.",
        )

        add_unique_risk(
            risk_items,
            "competition" in full_text
            or "competitors" in full_text
            or "competitive" in full_text
            or "hyperscaler" in full_text,
            "Hızlandırılmış hesaplama, yapay zeka çipleri ve hyperscaler müşteri segmentindeki rekabet NVIDIA’nın pazar konumunu ve fiyatlama gücünü etkileyebilir.",
        )

    elif ticker == "AMZN":
        add_unique_risk(
            risk_items,
            "aws" in full_text
            or "cloud" in full_text
            or "technology" in full_text
            or "data center" in full_text
            or "artificial intelligence" in full_text,
            "AWS, bulut altyapısı ve yapay zeka yatırımları yüksek sermaye harcaması, kapasite planlaması ve yoğun rekabet nedeniyle finansal sonuçlar üzerinde baskı oluşturabilir.",
        )

        add_unique_risk(
            risk_items,
            "fulfillment" in full_text
            or "logistics" in full_text
            or "transportation" in full_text
            or "delivery" in full_text
            or "labor" in full_text,
            "Lojistik, fulfillment ağı, teslimat operasyonları ve iş gücü maliyetleri Amazon’un operasyonel verimliliğini ve kâr marjlarını olumsuz etkileyebilir.",
        )

        add_unique_risk(
            risk_items,
            "inventory" in full_text
            or "supply" in full_text
            or "demand" in full_text
            or "supplier" in full_text,
            "Stok yönetimi, tedarik zinciri ve talep tahminlerindeki sapmalar maliyetleri artırabilir ve gelir zamanlamasını olumsuz etkileyebilir.",
        )

        add_unique_risk(
            risk_items,
            "regulation" in full_text
            or "regulatory" in full_text
            or "tax" in full_text
            or "antitrust" in full_text
            or "privacy" in full_text,
            "E-ticaret, pazar yeri, vergi, rekabet hukuku ve veri gizliliği alanındaki düzenleyici baskılar Amazon’un faaliyetlerini ve iş modelini etkileyebilir.",
        )

    elif ticker == "GOOGL":
        add_unique_risk(
            risk_items,
            "advertising" in full_text
            or "ads" in full_text
            or "search" in full_text
            or "youtube" in full_text,
            "Reklam pazarı, arama gelirleri ve YouTube ekosistemindeki talep değişimleri Alphabet’in ana gelir kaynakları üzerinde baskı oluşturabilir.",
        )

        add_unique_risk(
            risk_items,
            "artificial intelligence" in full_text
            or "ai" in full_text
            or "machine learning" in full_text
            or "cloud" in full_text,
            "Yapay zeka, arama deneyimi ve bulut hizmetlerindeki hızlı teknoloji değişimi yüksek yatırım ihtiyacı ve rekabet baskısı yaratabilir.",
        )

        add_unique_risk(
            risk_items,
            "privacy" in full_text
            or "data protection" in full_text
            or "security" in full_text
            or "regulation" in full_text
            or "regulatory" in full_text,
            "Veri gizliliği, kullanıcı verilerinin korunması ve düzenleyici yükümlülükler Alphabet’in reklam teknolojileri, ürün tasarımı ve faaliyet sonuçları üzerinde olumsuz etki yaratabilir.",
        )

        add_unique_risk(
            risk_items,
            "antitrust" in full_text
            or "competition" in full_text
            or "competitive" in full_text
            or "legal proceedings" in full_text,
            "Antitröst davaları, rekabet soruşturmaları ve yasal süreçler Alphabet’in iş modeli, ürün dağıtımı ve gelir yapısı üzerinde baskı oluşturabilir.",
        )

    if (
        "tariffs" in full_text
        or "inflation" in full_text
        or "interest rate" in full_text
        or "capital market" in full_text
        or "geopolitical" in full_text
        or "macroeconomic" in full_text
    ):
        add_unique_risk(
            risk_items,
            True,
            "Tarifeler, enflasyon, faiz oranları, sermaye piyasası oynaklığı ve jeopolitik gelişmeler operasyonel maliyetleri ve finansal sonuçları olumsuz etkileyebilir.",
        )

    return risk_items


def generate_source_based_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
) -> str:
    used_sources = []
    full_text = " ".join(chunk.get("text", "") for chunk in retrieved_chunks).lower()
    company_name = retrieved_chunks[0].get("company_name", "Şirket")
    ticker = retrieved_chunks[0].get("ticker", "")

    for index, chunk in enumerate(retrieved_chunks, start=1):
        used_sources.append(f"Kaynak {index}")

    risk_items = build_company_specific_risk_items(ticker, full_text)

    if not risk_items:
        risk_items.append(
            "İlgili kaynaklarda risk ifadeleri bulunuyor; ancak daha net sınıflama için embedding tabanlı retrieval veya daha güçlü bir local model kullanılabilir."
        )

    selected_risks = risk_items[:4]
    source_text = ", ".join(used_sources[:5])

    company_focus = {
        "AAPL": "ürün talebi, tedarik zinciri, Çin pazarı, App Store/regülasyon ve rekabet",
        "MSFT": "yapay zeka, Azure, bulut altyapısı, siber güvenlik, regülasyon ve rekabet",
        "NVDA": "yapay zeka, veri merkezi talebi, ihracat kontrolleri, Çin pazarı, tedarik ve rekabet",
        "AMZN": "AWS, lojistik, fulfillment operasyonları, regülasyon, iş gücü maliyetleri ve rekabet",
        "GOOGL": "yapay zeka, reklam pazarı, veri gizliliği, antitröst süreçleri, bulut ve rekabet",
    }

    focus_text = company_focus.get(
        ticker,
        "teknoloji dönüşümü, regülasyonlar, tedarik zinciri, rekabet ve operasyonel riskler",
    )

    lines = [
        (
            f"1. Kısa cevap: {ticker} - {company_name} için bulunan SEC 10-K kaynaklarında "
            f"{focus_text} başlıklarıyla bağlantılı riskler öne çıkıyor."
        ),
        "",
        "2. Öne çıkan riskler:",
    ]

    for risk in selected_risks:
        lines.append(f"- {risk}")

    lines.extend(
        [
            "",
            f"3. Kullanılan kaynaklar: {source_text}",
            "",
            "4. Uyarı: Bu çıktı yatırım tavsiyesi değildir; yalnızca SEC 10-K kaynaklarına dayalı araştırma amaçlı özetlemedir.",
        ]
    )

    return normalize_output_text("\n".join(lines))


def prepare_foundry_local(
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> Tuple[Any, Any, openai.OpenAI]:
    """
    Foundry Local modelini tek sefer yükler ve aynı Python oturumu boyunca cache'te tutar.

    Streamlit tarafında her buton tıklamasında script yeniden çalışsa bile import edilen
    rag_assistant modülü aynı process içinde kaldığı sürece model tekrar tekrar yüklenmez.
    """
    global _FOUNDRY_MANAGER
    global _FOUNDRY_MODEL
    global _FOUNDRY_CLIENT
    global _FOUNDRY_MODEL_ALIAS

    if (
        _FOUNDRY_MANAGER is not None
        and _FOUNDRY_MODEL is not None
        and _FOUNDRY_CLIENT is not None
        and _FOUNDRY_MODEL_ALIAS == model_alias
    ):
        print(f"Foundry Local modeli cache üzerinden kullanılıyor: {model_alias}")
        return _FOUNDRY_MANAGER, _FOUNDRY_MODEL, _FOUNDRY_CLIENT

    if _FOUNDRY_MANAGER is not None or _FOUNDRY_MODEL is not None:
        close_foundry_local(_FOUNDRY_MANAGER, _FOUNDRY_MODEL)

        _FOUNDRY_MANAGER = None
        _FOUNDRY_MODEL = None
        _FOUNDRY_CLIENT = None
        _FOUNDRY_MODEL_ALIAS = None

    print("Foundry Local başlatılıyor...")

    config = Configuration(app_name="nasdaq_financial_rag")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    try:
        manager.download_and_register_eps()
    except Exception as error:
        print(f"Execution provider kontrolü uyarı verdi: {error}")

    print(f"Model hazırlanıyor: {model_alias}")

    model = manager.catalog.get_model(model_alias)

    model.download(
        lambda progress: print(
            f"Model indiriliyor: {progress:.2f}%",
            end="",
            flush=True,
        )
    )

    print()

    model.load()
    print("Model yüklendi.")

    manager.start_web_service()

    base_url = f"{manager.urls[0]}/v1"

    client = openai.OpenAI(
        base_url=base_url,
        api_key="none",
    )

    _FOUNDRY_MANAGER = manager
    _FOUNDRY_MODEL = model
    _FOUNDRY_CLIENT = client
    _FOUNDRY_MODEL_ALIAS = model_alias

    return manager, model, client


def close_foundry_local(manager: Any, model: Any) -> None:
    if manager is not None:
        try:
            manager.stop_web_service()
            print("Foundry Local web servisi durduruldu.")
        except Exception as error:
            print(f"Web servisi durdurulurken uyarı oluştu: {error}")

    if model is not None:
        try:
            model.unload()
            print("Model bellekten çıkarıldı.")
        except Exception as error:
            print(f"Model unload sırasında uyarı oluştu: {error}")


def close_cached_foundry_local() -> None:
    """
    Uygulama kapanırken cache'te tutulan Foundry Local servisini ve modeli temizler.
    Normal Streamlit analizi sırasında çağrılmaz.
    """
    global _FOUNDRY_MANAGER
    global _FOUNDRY_MODEL
    global _FOUNDRY_CLIENT
    global _FOUNDRY_MODEL_ALIAS

    if _FOUNDRY_MANAGER is None and _FOUNDRY_MODEL is None:
        return

    close_foundry_local(_FOUNDRY_MANAGER, _FOUNDRY_MODEL)

    _FOUNDRY_MANAGER = None
    _FOUNDRY_MODEL = None
    _FOUNDRY_CLIENT = None
    _FOUNDRY_MODEL_ALIAS = None


atexit.register(close_cached_foundry_local)


def generate_with_foundry_client(
    prompt: str,
    client: openai.OpenAI,
    model_id: str,
) -> str:
    print("Foundry Local üzerinden cevap üretiliyor...")

    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=520,
    )

    return clean_answer(response.choices[0].message.content.strip())


def generate_with_foundry_local(
    prompt: str,
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> str:
    _, model, client = prepare_foundry_local(model_alias)
    return generate_with_foundry_client(prompt, client, model.id)


def answer_question(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 5,
    use_foundry_local: bool = True,
    foundry_client: Optional[openai.OpenAI] = None,
    foundry_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    retrieved_chunks = search_relevant_chunks(
        query=query,
        ticker=ticker,
        top_k=top_k,
    )

    if not retrieved_chunks:
        return {
            "query": query,
            "answer": "Bu soru için ilgili SEC 10-K kaynağı bulunamadı.",
            "sources": [],
        }

    context = build_context(retrieved_chunks)

    if DEBUG_CONTEXT:
        print("\n" + "=" * 80)
        print("MODELE GÖNDERİLEN CONTEXT")
        print("=" * 80)
        print(context)
        print("=" * 80 + "\n")

    prompt = build_user_prompt(query=query, context=context)

    if use_foundry_local:
        try:
            if foundry_client is not None and foundry_model_id is not None:
                answer = generate_with_foundry_client(
                    prompt=prompt,
                    client=foundry_client,
                    model_id=foundry_model_id,
                )
            else:
                answer = generate_with_foundry_local(prompt)

            if is_invalid_answer(answer):
                answer = generate_source_based_answer(query, retrieved_chunks)

        except Exception as error:
            print(f"Foundry Local cevap üretimi sırasında hata oluştu: {error}")
            answer = generate_source_based_answer(query, retrieved_chunks)
    else:
        answer = generate_source_based_answer(query, retrieved_chunks)

    answer = normalize_output_text(answer)

    return {
        "query": query,
        "answer": answer,
        "sources": retrieved_chunks,
    }


def answer_all_companies(
    query: Optional[str] = None,
    top_k: int = 5,
    use_foundry_local: bool = True,
) -> List[Dict[str, Any]]:
    results = []
    client = None
    model_id = None

    if use_foundry_local:
        _, model, client = prepare_foundry_local(DEFAULT_MODEL_ALIAS)
        model_id = model.id

    for ticker in SUPPORTED_COMPANIES:
        ticker_query = query if query else get_default_query(ticker)

        print()
        print("=" * 80)
        print(f"{ticker} analiz ediliyor...")
        print("=" * 80)
        print(f"Sorgu: {ticker_query}")

        result = answer_question(
            query=ticker_query,
            ticker=ticker,
            top_k=top_k,
            use_foundry_local=use_foundry_local,
            foundry_client=client,
            foundry_model_id=model_id,
        )

        results.append(result)

    return results


def print_rag_result(result: Dict[str, Any]) -> None:
    print("=" * 80)
    print("RAG CEVABI")
    print("=" * 80)
    print(result["answer"])

    print("\n" + "=" * 80)
    print("KULLANILAN KAYNAKLAR")
    print("=" * 80)

    for index, source in enumerate(result["sources"], start=1):
        print(f"{index}. {source.get('ticker')} - {source.get('company_name')}")
        print(f"   Filing: {source.get('filing_type')} | Tarih: {source.get('filing_date')}")
        print(f"   Section: {source.get('section')}")
        print(f"   Chunk ID: {source.get('chunk_id')}")
        print(f"   Skor: {source.get('score')}")
        print(f"   URL: {source.get('source_document_url')}")
        print("-" * 80)


def print_multiple_rag_results(results: List[Dict[str, Any]]) -> None:
    for result in results:
        sources = result.get("sources", [])

        if sources:
            ticker = sources[0].get("ticker")
            company_name = sources[0].get("company_name")
        else:
            ticker = "N/A"
            company_name = "Kaynak bulunamadı"

        print("\n" + "#" * 80)
        print(f"ŞİRKET ANALİZİ: {ticker} - {company_name}")
        print("#" * 80)
        print_rag_result(result)


def get_default_query(ticker: Optional[str]) -> str:
    if ticker == "AAPL":
        return "Apple son 10-K raporunda teknoloji, tedarik zinciri, rekabet, Çin pazarı ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "MSFT":
        return "Microsoft son 10-K raporunda yapay zeka, bulut, veri merkezi, siber güvenlik ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "NVDA":
        return "NVIDIA son 10-K raporunda yapay zeka, veri merkezi büyümesi, ihracat kontrolleri, Çin pazarı ve tedarik riskleriyle ilgili hangi konular öne çıkıyor?"

    if ticker == "AMZN":
        return "Amazon son 10-K raporunda AWS, lojistik, operasyonel maliyetler, regülasyon ve rekabet riskleriyle ilgili hangi konular öne çıkıyor?"

    if ticker == "GOOGL":
        return "Alphabet son 10-K raporunda yapay zeka, reklam pazarı, veri gizliliği, antitröst ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    return "AAPL, MSFT, NVDA, AMZN ve GOOGL şirketlerinin son 10-K raporlarında teknoloji, regülasyon, tedarik zinciri, rekabet ve operasyonel riskler açısından hangi konular öne çıkıyor?"


def choose_ticker() -> Optional[str]:
    print("Şirket seç:")
    print("AAPL  - Apple Inc.")
    print("MSFT  - Microsoft Corporation")
    print("NVDA  - NVIDIA Corporation")
    print("AMZN  - Amazon.com, Inc.")
    print("GOOGL - Alphabet Inc.")
    print("ALL   - Tüm şirketleri ayrı ayrı analiz et")

    selected_ticker = input("Ticker gir: ").strip().upper()

    if selected_ticker in {"ALL", "TUM", "TÜM", ""}:
        return None

    if selected_ticker not in SUPPORTED_COMPANIES:
        print("Geçersiz ticker girildi. Varsayılan olarak NVDA seçildi.")
        return "NVDA"

    return selected_ticker


def main() -> None:
    print("RAG Assistant test başlıyor...")

    ticker = choose_ticker()
    default_query = get_default_query(ticker)

    print("\nVarsayılan soru:")
    print(default_query)

    user_query = input("\nFarklı soru yazmak istersen yaz, yoksa Enter'a bas: ").strip()
    query = user_query if user_query else default_query

    if ticker is None:
        custom_query = user_query if user_query else None

        results = answer_all_companies(
            query=custom_query,
            top_k=5,
            use_foundry_local=True,
        )

        print_multiple_rag_results(results)
        return

    result = answer_question(
        query=query,
        ticker=ticker,
        top_k=5,
        use_foundry_local=True,
    )

    print_rag_result(result)


if __name__ == "__main__":
    main()