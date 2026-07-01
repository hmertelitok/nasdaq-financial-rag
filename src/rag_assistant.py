import re
from typing import Any, Dict, List, Optional, Tuple

import openai
from foundry_local_sdk import Configuration, FoundryLocalManager

from retriever import search_relevant_chunks


DEFAULT_MODEL_ALIAS = "qwen2.5-7b"
CONTEXT_CHUNK_CHAR_LIMIT = 1000
DEBUG_CONTEXT = False

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
    ]

    if any(term in lower_answer for term in invalid_terms):
        return True

    sentences = [sentence.strip() for sentence in answer.split(".") if sentence.strip()]
    unique_sentences = set(sentences)

    if len(sentences) >= 6 and len(unique_sentences) <= 3:
        return True

    if len(answer.strip()) < 40:
        return True

    return False


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

    risk_items = []

    if (
        "artificial intelligence" in full_text
        or "modern ai" in full_text
        or "accelerated computing" in full_text
        or "data center" in full_text
        or "datacenter" in full_text
        or "cloud" in full_text
        or "gpu" in full_text
        or "blackwell" in full_text
        or "technology" in full_text
    ):
        risk_items.append(
            "Teknoloji dönüşümü, yapay zeka, bulut veya veri merkezi ölçeğindeki büyüme; yüksek altyapı ihtiyacı, hızlı teknoloji değişimi ve müşteri gereksinimlerindeki dönüşüm nedeniyle operasyonel baskı oluşturabilir."
        )

    if (
        "privacy" in full_text
        or "security laws" in full_text
        or "data privacy" in full_text
        or "regulatory" in full_text
        or "regulation" in full_text
        or "legal proceedings" in full_text
        or "litigation" in full_text
    ):
        risk_items.append(
            "Veri gizliliği, güvenlik yasaları, regülasyonlar ve yasal süreçler itibar, ürün tasarımı, müşteri ilişkileri ve faaliyet sonuçları üzerinde olumsuz etki yaratabilir."
        )

    if (
        "supply" in full_text
        or "suppliers" in full_text
        or "purchase obligations" in full_text
        or "non-cancellable" in full_text
        or "non-returnable" in full_text
        or "demand" in full_text
        or "gross margins" in full_text
        or "inventory" in full_text
    ):
        risk_items.append(
            "Tedarik zinciri sorunları, satın alma taahhütleri, stok yönetimi ve arz-talep dengesindeki sapmalar maliyetleri, gelir zamanlamasını ve kâr marjlarını olumsuz etkileyebilir."
        )

    if (
        "china" in full_text
        or "export controls" in full_text
        or "restrictions" in full_text
        or "chinese government" in full_text
        or "international" in full_text
        or "foreign" in full_text
    ):
        risk_items.append(
            "Ülke bazlı kısıtlamalar, ihracat kontrolleri ve uluslararası düzenleyici baskılar gelirleri, rekabet gücünü ve uluslararası satışları baskılayabilir."
        )

    if (
        "competition" in full_text
        or "competitors" in full_text
        or "competitive" in full_text
        or "market share" in full_text
    ):
        risk_items.append(
            "Rekabet baskısı, alternatif teknolojiler ve pazar payı kaybı riski şirketin büyüme beklentilerini ve finansal performansını olumsuz etkileyebilir."
        )

    if (
        "tariffs" in full_text
        or "inflation" in full_text
        or "interest rate" in full_text
        or "capital market" in full_text
        or "geopolitical" in full_text
        or "global supply chain" in full_text
        or "guarantees" in full_text
        or "macroeconomic" in full_text
    ):
        risk_items.append(
            "Tarifeler, enflasyon, faiz oranları, jeopolitik gelişmeler ve makroekonomik koşullar operasyonel maliyetleri ve finansal sonuçları olumsuz etkileyebilir."
        )

    if not risk_items:
        risk_items.append(
            "İlgili kaynaklarda risk ifadeleri bulunuyor; ancak daha net sınıflama için embedding tabanlı retrieval veya daha güçlü bir local model kullanılabilir."
        )

    selected_risks = risk_items[:4]
    source_text = ", ".join(used_sources[:5])

    lines = [
        (
            f"1. Kısa cevap: {ticker} - {company_name} için bulunan SEC 10-K kaynaklarında "
            f"teknoloji dönüşümü, regülasyonlar, tedarik zinciri, rekabet ve makroekonomik koşullarla "
            f"bağlantılı riskler öne çıkıyor."
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
            f"\rModel indiriliyor: {progress:.2f}%",
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
    manager = None
    model = None

    try:
        manager, model, client = prepare_foundry_local(model_alias)
        return generate_with_foundry_client(prompt, client, model.id)

    finally:
        close_foundry_local(manager, model)


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
    query: str,
    top_k: int = 5,
    use_foundry_local: bool = True,
) -> List[Dict[str, Any]]:
    results = []
    manager = None
    model = None
    client = None

    try:
        if use_foundry_local:
            manager, model, client = prepare_foundry_local(DEFAULT_MODEL_ALIAS)

        for ticker in SUPPORTED_COMPANIES:
            print("\n" + "=" * 80)
            print(f"{ticker} analiz ediliyor...")
            print("=" * 80)

            result = answer_question(
                query=query,
                ticker=ticker,
                top_k=top_k,
                use_foundry_local=use_foundry_local,
                foundry_client=client,
                foundry_model_id=model.id if model is not None else None,
            )

            results.append(result)

    finally:
        if use_foundry_local:
            close_foundry_local(manager, model)

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
        return "Apple son 10-K raporunda teknoloji, tedarik zinciri, rekabet ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "MSFT":
        return "Microsoft son 10-K raporunda yapay zeka, bulut, veri merkezi ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "NVDA":
        return "NVIDIA son 10-K raporunda yapay zeka, veri merkezi büyümesi ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "AMZN":
        return "Amazon son 10-K raporunda bulut, lojistik, regülasyon ve operasyonel risklerle ilgili hangi konular öne çıkıyor?"

    if ticker == "GOOGL":
        return "Alphabet son 10-K raporunda yapay zeka, reklam pazarı, veri gizliliği ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?"

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
        results = answer_all_companies(
            query=query,
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