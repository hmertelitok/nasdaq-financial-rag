# Kurulum ve Çalıştırma Rehberi

Bu belge, NASDAQ Financial RAG Assistant projesinin Windows ve PowerShell ortamında yerel olarak çalıştırılmasını açıklar.

## Sistem Mimarisi

```text
Streamlit
    ↓
ASP.NET Core Web API — localhost:5094
    ↓
FastAPI AI Service — 127.0.0.1:8001
    ↓
PostgreSQL + pgvector — localhost:5433
    ↓
Microsoft Foundry Local — Qwen2.5-7B
```

## Gereksinimler

- Git
- Python ve `venv`
- .NET SDK
- Docker Desktop
- Microsoft Foundry Local
- PowerShell

Python paketleri `requirements.txt` üzerinden kurulmaktadır.

## 1. Projeyi Hazırlama

Projeyi klonlayın:

```powershell
git clone https://github.com/hmertelitok/nasdaq-financial-rag.git
cd nasdaq-financial-rag
```

Sanal ortamı oluşturun:

```powershell
python -m venv .venv
```

Sanal ortamı etkinleştirin:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"
```

Python paketlerini kurun:

```powershell
python -m pip install --upgrade pip
pip install -r .\requirements.txt
```

## 2. Ortam Değişkenleri

Örnek ortam dosyasını kopyalayın:

```powershell
Copy-Item .\.env.example .\.env
```

`.env` dosyasındaki `SEC_USER_AGENT` değerini gerçek ad ve iletişim e-postasıyla güncelleyin.

```env
SEC_USER_AGENT=Ad Soyad email@example.com
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=nasdaq_financial_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
NASDAQ_RAG_API_BASE_URL=http://localhost:5094
```

`.env` dosyası Git tarafından takip edilmez.

## 3. PostgreSQL ve pgvector

Docker Desktop'ın çalıştığından emin olun.

Proje harici bir Docker volume kullanır. İlk kurulumda volume oluşturun:

```powershell
docker volume create nasdaq_pgvector_data
```

PostgreSQL konteynerini başlatın:

```powershell
docker compose up -d
```

Konteyner durumunu kontrol edin:

```powershell
docker ps --filter "name=nasdaq-pgvector"
```

PostgreSQL bağlantısı:

```text
localhost:5433
```

> Hızlı başlangıç akışı, SEC filing ve chunk verilerinin PostgreSQL volume'una daha önce yüklenmiş olduğunu varsayar. Veri indirme ve yeniden indeksleme ayrı veri hazırlama akışıdır.

## 4. FastAPI AI Servisi

Yeni bir PowerShell terminalinde:

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn pgvector_search_service:app `
    --app-dir src `
    --host 127.0.0.1 `
    --port 8001
```

Sağlık kontrolü:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/health" |
    ConvertTo-Json
```

Temel FastAPI endpointleri:

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/health` | Servis sağlık kontrolü |
| GET | `/search` | pgvector semantic search |
| POST | `/ask` | Kaynak temelli RAG cevabı |

FastAPI terminalini açık bırakın.

## 5. ASP.NET Core Web API

İkinci PowerShell terminalinde:

```powershell
dotnet run --project .\api\NasdaqFinancialRag.Api\NasdaqFinancialRag.Api.csproj
```

Sağlık kontrolü:

```powershell
Invoke-RestMethod "http://localhost:5094/api/health" |
    ConvertTo-Json
```

RAG endpointi:

```text
POST /api/rag/ask
```

ASP.NET Core terminalini açık bırakın.

## 6. Streamlit Arayüzü

Üçüncü PowerShell terminalinde:

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run .\app\streamlit_app.py
```

Arayüz adresi:

```text
http://localhost:8501
```

Streamlit yalnızca ASP.NET Core API ile iletişim kurar. PostgreSQL, FastAPI veya Foundry Local bileşenlerine doğrudan bağlanmaz.

## 7. Başlatma Sırası

```text
1. Docker Desktop
2. PostgreSQL + pgvector
3. FastAPI
4. ASP.NET Core Web API
5. Streamlit
```

## 8. RAG Kalite Testi

FastAPI ve ASP.NET Core çalışırken:

```powershell
& ".\.venv\Scripts\python.exe" .\src\evaluate_rag_answer_quality.py `
    --output-dir .\reports\rag-quality
```

Beklenen sonuç:

```text
Toplam: 5 | Başarılı: 5 | Başarısız: 0
```

Raporlar:

```text
reports/rag-quality/rag_quality_evaluation.json
reports/rag-quality/rag_quality_evaluation.csv
```

## 9. Servisleri Durdurma

FastAPI, ASP.NET Core ve Streamlit terminallerinde:

```text
Ctrl + C
```

PostgreSQL konteynerini durdurun:

```powershell
docker compose stop
```

Tekrar başlatın:

```powershell
docker compose start
```

## Sorun Giderme

### WinError 10061

Bu hata, hedef servisin açık olmadığını gösterir:

```text
localhost:5094 → ASP.NET Core kapalı
127.0.0.1:8001 → FastAPI kapalı
```

### Port Kullanımda

8001 portunu kontrol edin:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

5094 portunu kontrol edin:

```powershell
Get-NetTCPConnection -LocalPort 5094 -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

### Docker Volume Bulunamadı

```powershell
docker volume create nasdaq_pgvector_data
docker compose up -d
```

### Streamlit API Bağlantısı Yok

ASP.NET Core sağlık endpointini test edin:

```powershell
Invoke-RestMethod "http://localhost:5094/api/health"
```

API adresi ortam değişkeniyle değiştirilebilir:

```powershell
$env:NASDAQ_RAG_API_BASE_URL = "http://localhost:5094"
```

## Yasal Uyarı

Bu proje yatırım tavsiyesi üretmez. Çıktılar yalnızca SEC raporları üzerinden araştırma, özetleme ve doküman temelli bilgi sunma amacı taşır.
