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
    "Yalnızca verilen kaynak metinlerini kullan. Kaynaklarda bulunmayan bilgiyi üretme. "
    "Cevabı doğal, profesyonel ve finans terminolojisine uygun Türkçe ile yaz. "
    "Aynı riski farklı cümlelerle tekrar etme. "
    "Her madde tek ve farklı bir risk kategorisini açıklasın. "
    "Her önemli iddianın sonunda [Kaynak N] göster. "
    "Riskleri olumlu sonuç gibi sunma. "
    "Kaynaklar yetersizse bunu açıkça belirt. "
    "Yatırım tavsiyesi verme ve düşünme sürecini paylaşma."
)

QUALITY_REPLACEMENTS = {
    "Güvenlik ve güvenlik": "Siber güvenlik",
    "güvenlik ve güvenlik": "siber güvenlik",
    "Doğal kaza": "Doğal afet",
    "doğal kaza": "doğal afet",
    "Yarışma": "Rekabet",
    "yarışma": "rekabet",
    "rekabet kurma": "rekabet etme",
    "Microsoft'in": "Microsoft'un",
    "Microsoft'e": "Microsoft'a",
    "satın almakistemelerini": "satın alma isteğini",
    "open-source foundation modelleri": "açık kaynak temel modelleri",
    "Open-source foundation modelleri": "Açık kaynak temel modelleri",
    "olumlu yönde etkileyebilir": "olumsuz etkileyebilir",
    "A W S": "AWS",
    "P R C": "Çin",
    "vekârlılığı": "ve kârlılığı",
}

FORBIDDEN_TERMS = (
    "güvenlik ve güvenlik",
    "doğal kaza",
    "yarışma",
    "hak ve izinler",
    "rekabet kurma",
    "satın almakistemelerini",
    "olumlu yönde etkileyebilir",
    "microsoft'in",
    "microsoft'e",
    "trump",
    "biden",
    "risk var",
    "kısıtlayıcı olabilir",
    "a w s",
    "p r c",
    "vekârlılığı",
    "telif hakkı ihlallerini koruması",
)

RISK_CATEGORIES: List[Dict[str, Any]] = [
    {
        "name": "export_controls",
        "title": "İhracat kontrolleri ve ülke kısıtlamaları",
        "keywords": (
            "export control",
            "export controls",
            "license requirement",
            "trade restriction",
            "restrictions",
            "china",
            "chinese government",
            "h20",
        ),
        "query_keywords": ("ihracat", "çin", "ülke", "kısıtlama"),
        "sentence": (
            "İhracat kontrol düzenlemeleri ve ülke bazlı kısıtlamalar, "
            "ürün satışlarını, müşteri talebini ve uluslararası rekabet gücünü olumsuz etkileyebilir."
        ),
    },
    {
        "name": "supply_chain",
        "title": "Tedarik zinciri ve üretim",
        "keywords": (
            "supply chain",
            "supplier",
            "manufacturing",
            "inventory",
            "purchase obligation",
            "non-cancellable",
            "fabrication",
            "foundry",
            "production capacity",
        ),
        "query_keywords": ("tedarik", "üretim", "arz", "stok"),
        "sentence": (
            "Tedarikçi bağımlılıkları, üretim kapasitesi ve arz-talep dengesindeki bozulmalar, "
            "ürün bulunabilirliğini, maliyetleri ve teslimat sürelerini olumsuz etkileyebilir."
        ),
    },
    {
        "name": "cybersecurity",
        "title": "Siber güvenlik ve teknik açıklar",
        "keywords": (
            "cybersecurity",
            "cyber attack",
            "ransomware",
            "security vulnerability",
            "vulnerabilities",
            "exploited",
            "malicious",
            "security incident",
            "hacking",
        ),
        "query_keywords": ("siber", "güvenlik", "açık"),
        "sentence": (
            "Siber saldırılar, yazılım açıkları ve üçüncü taraf güvenlik sorunları; "
            "hizmet kesintilerine, veri kaybına, müşteri güveninin zedelenmesine ve ek maliyetlere yol açabilir."
        ),
    },
    {
        "name": "privacy",
        "title": "Veri gizliliği ve kişisel veriler",
        "keywords": (
            "personal data",
            "privacy",
            "data protection",
            "collection",
            "retention",
            "transfer of personal data",
            "user data",
        ),
        "query_keywords": ("gizlilik", "kişisel veri", "veri koruma"),
        "sentence": (
            "Kişisel verilerin toplanması, korunması ve aktarılmasına ilişkin yükümlülükler; "
            "uyum maliyetlerini, hukuki sorumluluğu ve olası yaptırım riskini artırabilir."
        ),
    },
    {
        "name": "regulation",
        "title": "Düzenleyici uyum ve hukuki süreçler",
        "keywords": (
            "regulation",
            "regulatory",
            "compliance",
            "commission",
            "digital markets act",
            "dma",
            "antitrust",
            "legal proceedings",
            "fines",
            "penalties",
            "laws",
        ),
        "query_keywords": ("düzenleme", "regülasyon", "hukuk", "uyum"),
        "sentence": (
            "Değişen düzenlemeler, uyum yükümlülükleri ve hukuki süreçler; "
            "iş modelinde değişiklik, para cezası, ek maliyet ve faaliyet kısıtlaması doğurabilir."
        ),
    },
    {
        "name": "ai_technical",
        "title": "Yapay zekâ ve ürün güvenilirliği",
        "keywords": (
            "artificial intelligence",
            "ai features",
            "inaccurate content",
            "harmful content",
            "technical issues",
            "performance issues",
            "errors",
            "bugs",
            "defects",
            "safety risks",
        ),
        "query_keywords": ("yapay zeka", "yapay zekâ", "teknoloji", "ürün"),
        "sentence": (
            "Yapay zekâ ve diğer karmaşık teknolojilerdeki hata, güvenilirlik ve güvenlik sorunları; "
            "ürün performansını, kullanıcı deneyimini ve şirket itibarını olumsuz etkileyebilir."
        ),
    },
    {
        "name": "cloud_capacity",
        "title": "Bulut ve veri merkezi kapasitesi",
        "keywords": (
            "cloud",
            "azure",
            "data center",
            "datacenter",
            "capacity",
            "infrastructure",
            "computing infrastructure",
        ),
        "query_keywords": ("bulut", "azure", "veri merkezi", "kapasite"),
        "sentence": (
            "Bulut ve veri merkezi altyapısındaki kapasite, maliyet ve hizmet sürekliliği sorunları; "
            "müşteri hizmetlerini, büyüme planlarını ve kârlılığı olumsuz etkileyebilir."
        ),
    },
    {
        "name": "competition",
        "title": "Teknolojik değişim ve rekabet",
        "keywords": (
            "competition",
            "competitive",
            "technological advances",
            "market share",
            "pricing",
            "competitors",
            "rapid technological",
        ),
        "query_keywords": ("rekabet", "teknolojik değişim", "pazar"),
        "sentence": (
            "Hızlı teknolojik değişim ve yoğun rekabet; "
            "ürünlerin zamanında yenilenmesini zorlaştırabilir, fiyatlama gücünü ve pazar payını baskılayabilir."
        ),
    },
    {
        "name": "natural_disaster",
        "title": "İş sürekliliği ve doğal afetler",
        "keywords": (
            "natural disaster",
            "climate change",
            "extreme weather",
            "fire",
            "power shortage",
            "terrorist attack",
            "public health",
            "business interruption",
            "industrial accident",
        ),
        "query_keywords": ("doğal afet", "iklim", "iş sürekliliği"),
        "sentence": (
            "Doğal afetler, aşırı hava koşulları ve diğer iş kesintileri; "
            "üretim, teslimat, mağaza ve tesis operasyonlarını aksatabilir."
        ),
    },
    {
        "name": "demand",
        "title": "Talep ve pazar koşulları",
        "keywords": (
            "customer demand",
            "market demand",
            "demand",
            "product cycle",
            "macroeconomic",
            "economic conditions",
        ),
        "query_keywords": ("talep", "pazar", "makroekonomik"),
        "sentence": (
            "Müşteri talebindeki ve pazar koşullarındaki değişimler; "
            "satışları, kapasite planlamasını, stok seviyelerini ve finansal sonuçları olumsuz etkileyebilir."
        ),
    },
]


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
        "- Cevabı tamamen doğal ve profesyonel Türkçe ile yaz.\n"
        "- Birbirinden farklı 3 veya 4 kısa risk maddesi üret.\n"
        "- Aynı risk kategorisini iki ayrı maddede tekrar etme.\n"
        "- Her maddede riskin olası olumsuz etkisini açıkça belirt.\n"
        "- Her maddenin sonunda ilgili [Kaynak N] atfını kullan.\n"
        "- Kaynakta açıkça bulunmayan neden-sonuç ilişkisi kurma.\n"
        "- 'olumlu etki', 'yarışma', 'hak ve izinler', 'güvenlik ve güvenlik' "
        "ve 'doğal kaza' ifadelerini kullanma.\n"
        "- Şu terminolojiyi kullan: competition=rekabet, cybersecurity=siber güvenlik, "
        "natural disasters=doğal afetler, regulatory requirements=düzenleyici yükümlülükler.\n"
        "- Siyasi kişi veya yönetim adlarını gerekli değilse genel bir düzenleme ifadesiyle özetle.\n"
        "- Son satıra tam olarak 'Bu çıktı yatırım tavsiyesi değildir.' yaz.\n"
    )


def _apply_quality_replacements(text: str) -> str:
    result = text

    for wrong, correct in QUALITY_REPLACEMENTS.items():
        result = result.replace(wrong, correct)

    result = re.sub(r"(?<=[a-z??????])(?=[A-Z??????])", " ", result)
    result = re.sub(r"\[Kaynak\s*(\d+)\]", r"[Kaynak \1]", result, flags=re.IGNORECASE)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r" +\n", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


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

        comparison_key = normalized.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        lines.append(normalized)

    result = _apply_quality_replacements("\n".join(lines))

    if "Bu çıktı yatırım tavsiyesi değildir." not in result:
        result = f"{result}\n\nBu çıktı yatırım tavsiyesi değildir.".strip()

    return result


def _extract_risk_lines(answer: str) -> List[str]:
    return [
        line.strip()
        for line in answer.splitlines()
        if re.match(r"^(?:[-•]|\d+[.)])\s+", line.strip())
    ]


def _is_low_quality_answer(answer: str) -> bool:
    lowered = answer.casefold()
    risk_lines = _extract_risk_lines(answer)

    if any(term in lowered for term in FORBIDDEN_TERMS):
        return True

    if len(risk_lines) < 3 or len(risk_lines) > 4:
        return True

    if any(len(line) > 420 for line in risk_lines):
        return True

    if re.search(
        r"\b(?:[A-ZÇĞİÖŞÜ]\s+){2,}[A-ZÇĞİÖŞÜ]\b",
        answer,
    ):
        return True

    if re.search(
        r"\[Kaynak\d+\]",
        answer,
        flags=re.IGNORECASE,
    ):
        return True

    if any("[kaynak " not in line.casefold() for line in risk_lines):
        return True

    if "bu çıktı yatırım tavsiyesi değildir." not in lowered:
        return True

    source_numbers = re.findall(r"\[Kaynak\s+(\d+)\]", answer, flags=re.IGNORECASE)
    if len(source_numbers) < len(risk_lines):
        return True

    normalized_lines = []
    for line in risk_lines:
        without_source = re.sub(
            r"\[Kaynak\s+\d+\]",
            "",
            line,
            flags=re.IGNORECASE,
        )
        words = {
            word
            for word in re.findall(
                r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
                without_source.casefold(),
            )
            if len(word) >= 5
        }
        normalized_lines.append(words)

    for index, first in enumerate(normalized_lines):
        for second in normalized_lines[index + 1 :]:
            union = first | second
            if not union:
                continue
            overlap = len(first & second) / len(union)
            if overlap >= 0.45:
                return True

    return False


def _score_category(
    category: Dict[str, Any],
    query: str,
    results: List[Dict[str, Any]],
) -> Tuple[int, Optional[int]]:
    score = 0
    best_source_index: Optional[int] = None
    best_source_score = 0
    query_lower = query.casefold()

    for query_keyword in category["query_keywords"]:
        if query_keyword.casefold() in query_lower:
            score += 3

    for source_index, result in enumerate(results, start=1):
        excerpt = str(
            result.get("excerpt")
            or result.get("chunk_text")
            or ""
        ).casefold()

        source_score = 0
        for keyword in category["keywords"]:
            occurrences = excerpt.count(keyword.casefold())
            if occurrences:
                source_score += min(occurrences, 3)

        if source_score > best_source_score:
            best_source_score = source_score
            best_source_index = source_index

        score += source_score

    return score, best_source_index


def _build_deterministic_answer(
    query: str,
    results: List[Dict[str, Any]],
) -> str:
    if not results:
        return (
            "Bu soru için ilgili SEC kaynağı bulunamadı.\n\n"
            "Bu çıktı yatırım tavsiyesi değildir."
        )

    ticker = str(results[0].get("ticker") or "İlgili şirket")
    scored_categories: List[Tuple[int, int, Dict[str, Any]]] = []

    for order, category in enumerate(RISK_CATEGORIES):
        score, source_index = _score_category(category, query, results)

        if score > 0 and source_index is not None:
            scored_categories.append((score, -order, {
                **category,
                "source_index": source_index,
            }))

    scored_categories.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )

    selected = [item[2] for item in scored_categories[:4]]

    if len(selected) < 3:
        for fallback_index, result in enumerate(results, start=1):
            if len(selected) >= 3:
                break

            excerpt = str(
                result.get("excerpt")
                or result.get("chunk_text")
                or ""
            ).casefold()

            if "risk" in excerpt or "adversely affect" in excerpt:
                generic_name = f"generic_{fallback_index}"
                if any(item["name"] == generic_name for item in selected):
                    continue

                selected.append(
                    {
                        "name": generic_name,
                        "title": "Operasyonel ve finansal riskler",
                        "sentence": (
                            "Kaynakta açıklanan operasyonel belirsizlikler; "
                            "faaliyetlerin sürekliliğini, maliyetleri ve finansal sonuçları olumsuz etkileyebilir."
                        ),
                        "source_index": fallback_index,
                    }
                )

    lines = [
        f"{ticker} için SEC kaynaklarında öne çıkan temel riskler:",
        "",
    ]

    for category in selected:
        lines.append(
            f"- {category['title']}: {category['sentence']} "
            f"[Kaynak {category['source_index']}]"
        )

    lines.extend(
        [
            "",
            "Bu çıktı yatırım tavsiyesi değildir.",
        ]
    )

    return _apply_quality_replacements("\n".join(lines))


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


def _generate_with_client(
    client: openai.OpenAI,
    model_id: str,
    prompt: str,
) -> str:
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=520,
    )

    content = response.choices[0].message.content or ""
    return _clean_answer(content)


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
    _, model, client = prepare_foundry_local(model_alias)

    model_answer = _generate_with_client(
        client=client,
        model_id=model.id,
        prompt=_build_prompt(query=query, context=context),
    )

    if _is_low_quality_answer(model_answer):
        print(
            "Model cevabı kalite kontrolünden geçemedi; "
            "kaynak-temelli kontrollü cevap kullanılıyor."
        )
        return _build_deterministic_answer(query, results)

    return model_answer


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
