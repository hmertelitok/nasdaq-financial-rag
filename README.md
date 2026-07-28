# NASDAQ Financial RAG Assistant

Microsoft AI Innovators Summer Internship programı kapsamında geliştirilen **NASDAQ Financial RAG Assistant**, seçili NASDAQ şirketlerinin SEC 10-K raporları üzerinde çalışan Türkçe bir finansal araştırma asistanıdır.

Sistem; kullanıcı sorusuyla ilgili rapor parçalarını PostgreSQL ve pgvector üzerinden getirir, Microsoft Foundry Local üzerinde çalışan yerel dil modeliyle kaynak temelli yanıt üretir ve cevabın dayandığı filing, section, chunk ve benzerlik skorlarını kullanıcıya gösterir.

> Bu proje yatırım tavsiyesi üretmez. SEC raporlarının araştırılması, özetlenmesi ve kaynak temelli analiz edilmesi amacıyla geliştirilmiştir.

---
## Hızlı Başlangıç (ZIP ile)

Kurulumla uğraşmak istemiyor musunuz? Sadece 3 adımda çalıştırın:

### 1. ZIP Dosyalarını İndirin
[Releases sayfasından](https://github.com/hmertelitok/nasdaq-financial-rag/releases) en son sürümü indirin:
- `Nasdaq-Dotnet-API.zip` (45.9 MB)
- `Nasdaq-Python-App.zip` (66.7 KB)

### 2. ZIP'leri Çıkartın
Her iki ZIP dosyasını da ayrı klasörlere çıkartın.

### 3. Çalıştırın
**Önce .NET API'yi başlatın:**
1. `Nasdaq-Dotnet-API` klasörüne gidin
2. `baslat.bat` dosyasına çift tıklayın
3. Bir terminal penceresi açılacak ve API başlayacak

**Sonra Python Servislerini başlatın:**
1. `Nasdaq-Python-App` klasörüne gidin
2. `baslat.bat` dosyasına çift tıklayın
3. Otomatik olarak FastAPI ve Streamlit başlayacak

### 4. Tarayıcınızı Açın
- **Streamlit Dashboard:** http://localhost:8501
- **FastAPI Docs:** http://127.0.0.1:8001/docs

### Gereksinimler
- Windows 10/11
- Docker Desktop (çalışır durumda)
- Python 3.11+ (otomatik kurulur)
- .NET SDK (gerekmez - self-contained)

### Durdurmak İçin
Tüm terminal pencerelerini kapatın ve:
```bash
docker-compose down
# Uygulama Görselleri

## Streamlit Arayüzü

ASP.NET Core, FastAPI, PostgreSQL + pgvector ve Microsoft Foundry Local bileşenlerini tek bir araştırma arayüzünde birleştiren kontrol paneli.

![NASDAQ Financial RAG Dashboard](docs/images/streamlit-dashboard.png)

---

## Kaynak Temelli RAG Cevabı

Kullanıcı soruları, seçilen SEC 10-K rapor parçaları kullanılarak kaynak referanslarıyla yanıtlanır.

![NASDAQ Financial RAG Result](docs/images/streamlit-rag-result.png)

---

## Kaynak Şeffaflığı

Her cevap için şirket, filing tarihi, bölüm, chunk ID, benzerlik skoru, retrieval türü ve embedding modeli görüntülenir.

![NASDAQ Financial RAG Source Details](docs/images/streamlit-source-details.png)

<details>
<summary>Orijinal SEC 10-K kaynağını görüntüle</summary>

<br>

![Microsoft SEC 10-K Filing](docs/images/sec-filing-verification.png)

</details>

---

# Proje Amacı

SEC 10-K raporları uzun, teknik ve manuel olarak incelenmesi zaman alan finansal dokümanlardır.

Bu projenin amacı, genel amaçlı bir chatbot geliştirmek yerine;

- Gerçek SEC dokümanları üzerinde çalışan
- Yanıtlarını kaynak parçalarıyla destekleyen
- Yerel model ve yerel veri altyapısı kullanabilen
- Python ve ASP.NET Core servislerini birlikte kullanan
- Yanıt kalitesini otomatik kontrollerle denetleyen
- Kaynak şeffaflığını kullanıcı arayüzünde gösteren

bir finansal RAG sistemi oluşturmaktır.

---

# Desteklenen Şirketler

| Ticker | Şirket |
|---------|---------|
| AAPL | Apple Inc. |
| MSFT | Microsoft Corporation |
| NVDA | NVIDIA Corporation |
| AMZN | Amazon.com, Inc. |
| GOOGL | Alphabet Inc. |

---

# Veri Kaynağı

Projede SEC EDGAR üzerinden alınan 10-K raporları kullanılmaktadır.

Mevcut veri setinde:

- 5 şirket
- 5 SEC filing
- 334 doküman parçası

bulunmaktadır.

---

# Temel Özellikler

- SEC 10-K raporlarını indirme ve işleme
- Finansal doküman temizleme ve chunking
- Çok dilli embedding üretimi
- PostgreSQL ve pgvector üzerinde vektör saklama
- Semantic Search ile ilgili doküman parçalarını getirme
- Microsoft Foundry Local ile yerel yanıt üretimi
- Türkçe ve kaynak temelli RAG cevapları
- `[Kaynak N]` biçiminde kaynak atıfları
- Filing type, section, chunk ve benzerlik skoru gösterimi
- FastAPI tabanlı dahili AI servisi
- ASP.NET Core Web API
- Tek şirket ve tüm şirketlerde analiz
- Dinamik örnek sorular
- API hata yönetimi
- Yükleme durumu ve analiz ilerleme göstergeleri
- Otomatik RAG cevap kalite değerlendirmesi
- JSON ve CSV kalite raporları
- Modern Streamlit arayüzü

---

# Kullanılan Teknolojiler

## AI ve Veri İşleme

- Python
- Microsoft Foundry Local
- Qwen2.5-7B
- `intfloat/multilingual-e5-small`
- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Embeddings

## Backend

- FastAPI
- ASP.NET Core Web API
- C#

## Veri Katmanı

- PostgreSQL
- pgvector
- SEC EDGAR

## Arayüz

- Streamlit

---

# Orkestrasyon Framework Kararı

Mevcut RAG hattı belirli, kontrollü ve test edilebilir olduğu için Semantic Kernel veya Microsoft Agent Framework bu sürüme eklenmemiştir.

Bu kararla:

- Deterministik RAG mimarisi korunmuştur.
- Retrieval, cevap üretimi ve kalite kontrolü mevcut servis sınırlarında tutulmuştur.
- Gereksiz framework bağımlılığı önlenmiştir.
- Agent tabanlı orchestration ileride gerçek ihtiyaç oluştuğunda değerlendirilecektir.

Detay:

```
docs/orchestration_framework_assessment.md
```

---

# Güncel Sistem Mimarisi

```text
SEC EDGAR 10-K Reports
          │
          ▼
Python Data Processing
Cleaning → Chunking → Embeddings
          │
          ▼
PostgreSQL + pgvector
          │
          ▼
FastAPI AI Service
/search → /ask
          │
          ▼
Microsoft Foundry Local
Qwen2.5-7B
          │
          ▼
ASP.NET Core Web API
          │
          ▼
Streamlit / API Clients
```

---

# Servis Sorumlulukları

## Python

- SEC veri işleme
- Metin temizleme
- Chunking
- Embedding üretimi
- pgvector semantic search
- Foundry Local entegrasyonu
- RAG cevap üretimi
- Kalite değerlendirmesi

---

## FastAPI

ASP.NET Core tarafından kullanılan dahili AI servisidir.

| Method | Endpoint | Açıklama |
|---------|----------|----------|
| GET | /health | Sağlık kontrolü |
| GET | /search | Semantic Search |
| POST | /ask | Kaynak temelli RAG cevabı |

---

## ASP.NET Core Web API

Sistemin dış API katmanıdır.

| Method | Endpoint | Açıklama |
|---------|----------|----------|
| GET | /api/health | API sağlık kontrolü |
| GET | /api/postgres/companies | Şirketler |
| GET | /api/postgres/stats/summary | Veri özeti |
| GET | /api/postgres/filings | Filing kayıtları |
| GET | /api/postgres/chunks | Chunk listesi |
| GET | /api/postgres/search | Semantic Search |
| POST | /api/rag/ask | RAG cevabı |

---

# RAG Cevap Kalite Sistemi

Projede yalnızca HTTP cevabının başarılı olması değil, üretilen cevabın içerik kalitesi de otomatik olarak doğrulanmaktadır.

Kontroller:

- HTTP 200
- Cevap varlığı
- En az üç kaynak
- Beklenen madde sayısı
- Her maddede kaynak atfı
- Atıf aralığı doğrulaması
- `[Kaynak N]` biçimi
- Bozulmuş kaynak gösterimi kontrolü
- Birleşmiş kelime hataları
- Madde uzunluğu
- Yatırım tavsiyesi uyarısı
- Düşük kaliteli ifadeler
- Tekrarlayan maddeler
- Türkçe dil kontrolü
- Makul cevap uzunluğu

---

# Kalite Değerlendirme Sonucu

14 Temmuz 2026 tarihinde gerçekleştirilen otomatik kalite testlerinde sistem tüm şirketlerde başarılı sonuç üretmiştir.

| Ticker | Sonuç | HTTP | Kaynak | Madde | Atıf |
|---------|------|------|---------|-------|------|
| AAPL | PASS | 200 | 5 | 4 | 4 |
| MSFT | PASS | 200 | 5 | 4 | 4 |
| NVDA | PASS | 200 | 5 | 4 | 4 |
| AMZN | PASS | 200 | 5 | 4 | 4 |
| GOOGL | PASS | 200 | 5 | 4 | 4 |

```text
Toplam      : 5
Başarılı    : 5
Başarısız   : 0
Başarı Oranı: %100
```

Raporlar:

```
reports/rag-quality/rag_quality_evaluation.json
reports/rag-quality/rag_quality_evaluation.csv
```

Çalıştırma:

```powershell
& ".\.venv\Scripts\python.exe" .\src\evaluate_rag_answer_quality.py `
    --output-dir .\reports\rag-quality
```

---

# Örnek Sorular

```text
Microsoft'un bulut bilişim ve yapay zekâ yatırımları şirketin büyüme stratejisini nasıl destekliyor?
```

```text
NVIDIA'nın tedarik zinciri, ihracat kontrolleri ve yapay zekâ talebiyle ilgili riskleri nelerdir?
```

```text
Apple'ın temel iş riskleri nelerdir?
```

```text
Amazon'un AWS, lojistik, operasyonel maliyetler ve düzenleyici riskleri nelerdir?
```

---

# Proje Durumu

Tamamlanan bileşenler:

- SEC veri işleme hattı
- Metin temizleme
- Chunking
- Embedding
- PostgreSQL
- pgvector
- Semantic Search
- FastAPI
- Microsoft Foundry Local
- ASP.NET Core Web API
- Kaynak temelli RAG
- Kalite değerlendirme sistemi
- JSON/CSV raporları
- Streamlit arayüzü
- Uçtan uca testler
- Kurulum dokümantasyonu

---

# Kurulum ve Çalıştırma

> **Docker Notu**
>
> `docker-compose.yml` yalnızca PostgreSQL + pgvector servisini container içerisinde çalıştırır.
>
> Microsoft Foundry Local, Windows/WinML donanım hızlandırmasına ihtiyaç duyduğu için FastAPI, ASP.NET Core ve Streamlit host makine üzerinde çalıştırılır.

Ayrıntılı kurulum:

```
docs/setup_and_run.md
```

Servis sırası:

```text
PostgreSQL + pgvector
          │
          ▼
FastAPI
          │
          ▼
ASP.NET Core
          │
          ▼
Streamlit
```

---

# API Dokümantasyonu

```
docs/postgres_pgvector_api.md
```

---

# Yasal Uyarı

Bu proje yatırım tavsiyesi vermez.

Üretilen cevaplar yalnızca SEC 10-K raporları üzerinden araştırma, özetleme ve doküman temelli bilgi sunmak amacıyla hazırlanmıştır. Finansal kararlar için tek başına kullanılmamalıdır.
