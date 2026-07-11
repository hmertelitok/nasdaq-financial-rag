from __future__ import annotations

import atexit
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import openai
from foundry_local_sdk import Configuration, FoundryLocalManager

from pgvector_search import EMBEDDING_MODEL_NAME, semantic_search


DEFAULT_MODEL_ALIAS = "qwen2.5-7b"
CONTEXT_CHUNK_CHAR_LIMIT = 1400

_FOUNDRY_MANAGER: Optional[Any] = None
_FOUNDRY_MODEL: Optional[Any] = None
_FOUNDRY_CLIENT: Optional[openai.OpenAI] = None
_FOUNDRY_MODEL_ALIAS: Optional[str] = None

SYSTEM_MESSAGE = (
    "Sen SEC şirket raporlarına dayalı çalışan bir finansal araştırma asistanısın. "
    "Yalnızca verilen kaynak metinleri kullan. Kaynaklarda bulunmayan bilgiyi üretme. "
    "Cevabı Türkçe, açık ve kısa yaz. Önemli iddiaların sonunda [Kaynak N] göster. "
    "Kaynaklar soruyu yanıtlamak için yetersizse bunu açıkça belirt. "
    "Yatırım tavsiyesi verme ve düşünme sürecini paylaşma."
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _trim_text(text: str, max_chars: int = CONTEXT_CHUNK_CHAR_LIMIT) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _build_context(results: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []

    for index, result in enumerate(results, start=1):
        excerpt = result.get("excerpt") or result.get("chunk_text") or ""
        blocks.append(
            "\n".join(
                [
                    f"Kaynak {index}",
                    f"Ticker: {result.get('ticker') or 'N/A'}",
                    f"Dosya türü: {result.get('filing_type') or 'N/A'}",
                    f"Dosya tarihi: {_json_safe(result.get('filing_date')) or 'N/A'}",
                    f"Bölüm: {result.get('section') or 'N/A'}",
                    f"Benzerlik: {float(result.get('similarity') or 0):.4f}",
                    f"Metin: {_trim_text(str(excerpt))}",
                ]
            )
        )

    return "\n\n".join(blocks)


def _build_prompt(query: str, context: str) -> str:
    return (
        f"Kullanıcı sorusu:\n{query}\n\n"
        f"SEC kaynakları:\n{context}\n\n"
        "Görev:\n"
        "- Soruyu yalnızca yukarıdaki SEC kaynaklarına dayanarak yanıtla.\n"
        "- Cevabı tamamen Türkçe yaz.\n"
        "- En fazla 5 kısa madde kullan.\n"
        "- Her önemli iddianın sonunda [Kaynak N] göster.\n"
        "- Kaynaklarda bulunmayan bir çıkarım yapma.\n"
        "- Son satıra 'Bu çıktı yatırım tavsiyesi değildir.' yaz."
    )


def _clean_answer(answer: str) -> str:
    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        answer or "",
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = cleaned.replace("<think>", "").replace("</think>", "").strip()

    lines: List[str] = []
    seen: set[str] = set()

    for line in cleaned.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            if lines and lines[-1] != "":
                lines.append("")
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        lines.append(normalized)

    result = "\n".join(lines).strip()

    if "Bu çıktı yatırım tavsiyesi değildir." not in result:
        result = f"{result}\n\nBu çıktı yatırım tavsiyesi değildir.".strip()

    return result


def prepare_foundry_local(
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> Tuple[Any, Any, openai.OpenAI]:
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
        return _FOUNDRY_MANAGER, _FOUNDRY_MODEL, _FOUNDRY_CLIENT

    if _FOUNDRY_MANAGER is not None or _FOUNDRY_MODEL is not None:
        close_foundry_local()

    config = Configuration(app_name="nasdaq_financial_rag_pgvector")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    try:
        manager.download_and_register_eps()
    except Exception as error:
        print(f"Execution provider kontrol uyarısı: {error}")

    model = manager.catalog.get_model(model_alias)
    model.download(
        lambda progress: print(
            f"Model hazırlanıyor: %{progress:.2f}",
            end="\r",
            flush=True,
        )
    )
    print()

    model.load()
    manager.start_web_service()

    client = openai.OpenAI(
        base_url=f"{manager.urls[0]}/v1",
        api_key="none",
    )

    _FOUNDRY_MANAGER = manager
    _FOUNDRY_MODEL = model
    _FOUNDRY_CLIENT = client
    _FOUNDRY_MODEL_ALIAS = model_alias

    return manager, model, client


def close_foundry_local() -> None:
    global _FOUNDRY_MANAGER
    global _FOUNDRY_MODEL
    global _FOUNDRY_CLIENT
    global _FOUNDRY_MODEL_ALIAS

    if _FOUNDRY_MANAGER is not None:
        try:
            _FOUNDRY_MANAGER.stop_web_service()
        except Exception as error:
            print(f"Foundry Local web servisi kapatılırken uyarı: {error}")

    if _FOUNDRY_MODEL is not None:
        try:
            _FOUNDRY_MODEL.unload()
        except Exception as error:
            print(f"Foundry Local modeli kaldırılırken uyarı: {error}")

    _FOUNDRY_MANAGER = None
    _FOUNDRY_MODEL = None
    _FOUNDRY_CLIENT = None
    _FOUNDRY_MODEL_ALIAS = None


atexit.register(close_foundry_local)


def generate_answer(
    query: str,
    results: List[Dict[str, Any]],
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> str:
    if not results:
        return (
            "Bu soru için ilgili SEC kaynağı bulunamadı.\n\n"
            "Bu çıktı yatırım tavsiyesi değildir."
        )

    context = _build_context(results)
    prompt = _build_prompt(query=query, context=context)
    _, model, client = prepare_foundry_local(model_alias)

    response = client.chat.completions.create(
        model=model.id,
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=650,
    )

    content = response.choices[0].message.content or ""
    return _clean_answer(content)


def answer_question(
    query: str,
    ticker: Optional[str] = None,
    section: Optional[str] = None,
    top_k: int = 5,
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> Dict[str, Any]:
    normalized_ticker = ticker.strip().upper() if ticker else None
    normalized_section = section.strip() if section else None
    safe_top_k = max(1, min(top_k, 20))

    results = semantic_search(
        query=query,
        ticker=normalized_ticker,
        section=normalized_section,
        limit=safe_top_k,
    )

    answer = generate_answer(
        query=query,
        results=results,
        model_alias=model_alias,
    )

    serialized_sources = [
        {key: _json_safe(value) for key, value in result.items()}
        for result in results
    ]

    return {
        "query": query,
        "ticker": normalized_ticker,
        "section": normalized_section,
        "topK": safe_top_k,
        "embeddingModel": EMBEDDING_MODEL_NAME,
        "generationModel": model_alias,
        "answer": answer,
        "sourceCount": len(serialized_sources),
        "sources": serialized_sources,
    }
