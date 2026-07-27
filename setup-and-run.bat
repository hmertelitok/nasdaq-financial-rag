@echo off
chcp 65001 >nul
title Nasdaq Financial RAG - Otomatik Kurulum ve Baslatma
color 0A

echo.
echo ========================================
echo   NASDAQ FINANCIAL RAG
echo   Otomatik Kurulum ve Baslatma
echo ========================================
echo.

REM ============================================
REM 1. DIZIN KONTROLU
REM ============================================
if not exist "docker-compose.yml" (
    color 0C
    echo [HATA] docker-compose.yml dosyasi bulunamadi!
    echo Bu script'i projenin ana dizininden calistirmalisiniz.
    pause
    exit /b 1
)

REM ============================================
REM 2. DOCKER KONTROLU
REM ============================================
echo [1/6] Docker kontrol ediliyor...
docker ps >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [HATA] Docker Desktop calismiyor veya yuklu degil!
    echo Lutfen Docker Desktop'i baslatin ve tekrar deneyin.
    pause
    exit /b 1
)
echo [OK] Docker calisiyor.
echo.

REM ============================================
REM 3. DOCKER VOLUME KONTROLU
REM ============================================
echo [2/6] Docker volume kontrol ediliyor...
docker volume ls | findstr nasdaq_pgvector_data >nul
if errorlevel 1 (
    echo [BILGI] Volume bulunamadi, olusturuluyor...
    docker volume create nasdaq_pgvector_data
    echo [OK] Volume olusturuldu.
) else (
    echo [OK] Volume zaten mevcut.
)
echo.

REM ============================================
REM 4. .ENV DOSYASI KONTROLU
REM ============================================
echo [3/6] .env dosyasi kontrol ediliyor...
if not exist ".env" (
    if exist ".env.example" (
        echo [BILGI] .env dosyasi bulunamadi, .env.example'dan kopyalaniyor...
        copy .env.example .env >nul
        echo.
        color 0E
        echo [ONEM] Lutfen .env dosyasini duzenleyin:
        echo   - API anahtarlarinizi ekleyin
        echo   - Veritabani sifresini kontrol edin
        echo.
        echo Dosyayi acmak icin bir tusa basin...
        pause >nul
        notepad .env
        echo.
        echo .env dosyasini kaydettikten sonra devam etmek icin bir tusa basin...
        pause >nul
        color 0A
    ) else (
        color 0C
        echo [HATA] .env.example dosyasi bulunamadi!
        pause
        exit /b 1
    )
) else (
    echo [OK] .env dosyasi mevcut.
)
echo.

REM ============================================
REM 5. PYTHON VENV VE BAGIMLILIKLAR
REM ============================================
echo [4/6] Python ortam hazirlaniyor...
if not exist ".venv" (
    echo [BILGI] Virtual environment olusturuluyor...
    python -m venv .venv
    if errorlevel 1 (
        color 0C
        echo [HATA] Python yuklu degil veya venv olusturulamadi!
        echo Python 3.11+ yuklemeniz gerekiyor.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment olusturuldu.
) else (
    echo [OK] Virtual environment zaten mevcut.
)

echo [BILGI] Python bagimliliklari yukleniyor...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    color 0C
    echo [HATA] Bagimliliklar yuklenemedi!
    pause
    exit /b 1
)
echo [OK] Bagimliliklar yuklendi.
echo.

REM ============================================
REM 6. .NET API DERLEME
REM ============================================
echo [5/6] .NET API derleniyor...
if exist ".api\NasdaqFinancialRag.Api\NasdaqFinancialRag.Api.csproj" (
    dotnet build .api\NasdaqFinancialRag.Api\NasdaqFinancialRag.Api.csproj --configuration Release
    if errorlevel 1 (
        color 0C
        echo [HATA] .NET API derlenemedi!
        echo .NET 8.0 SDK yuklemeniz gerekiyor.
        pause
        exit /b 1
    )
    echo [OK] .NET API derlendi.
) else (
    color 0E
    echo [UYARI] .NET API projesi bulunamadi, atlanıyor...
)
echo.

REM ============================================
REM 7. DOCKER COMPOSE BASLATMA
REM ============================================
echo [6/6] Docker servisleri baslatiliyor...
docker-compose up -d
if errorlevel 1 (
    color 0C
    echo [HATA] Docker servisleri baslatilamadi!
    pause
    exit /b 1
)
echo [OK] Docker servisleri baslatildi.
echo.

REM ============================================
REM 8. SERVISLERI BASLATMA
REM ============================================
echo ========================================
echo   KURULUM TAMAMLANDI!
echo ========================================
echo.
echo Servisler baslatiliyor...
echo.

REM FastAPI servisi (Port 8001)
echo [1/3] FastAPI AI Service baslatiliyor (Port 8001)...
start "FastAPI - Nasdaq Financial RAG" cmd /k "title FastAPI Service && color 0B && echo FastAPI servisi baslatildi... && echo Port: http://127.0.0.1:8001 && echo. && .venv\Scripts\python.exe -m uvicorn pgvector_search_service:app --app-dir src --host 127.0.0.1 --port 8001 --reload"

REM ASP.NET Core API (Port 5000 veya 8000)
if exist ".api\NasdaqFinancialRag.Api\NasdaqFinancialRag.Api.csproj" (
    echo [2/3] ASP.NET Core API baslatiliyor...
    start "ASP.NET Core API - Nasdaq Financial RAG" cmd /k "title ASP.NET Core API && color 0D && echo ASP.NET Core API baslatildi... && echo Port: http://127.0.0.1:5000 && echo. && dotnet run --project .api\NasdaqFinancialRag.Api\NasdaqFinancialRag.Api.csproj"
) else (
    echo [2/3] ASP.NET Core API atlandi (proje bulunamadi).
)

REM Streamlit App
if exist ".app\streamlit_app.py" (
    echo [3/3] Streamlit App baslatiliyor...
    start "Streamlit - Nasdaq Financial RAG" cmd /k "title Streamlit App && color 0E && echo Streamlit App baslatildi... && echo Port: http://localhost:8501 && echo. && .venv\Scripts\python.exe -m streamlit run .app\streamlit_app.py"
) else (
    echo [3/3] Streamlit App atlandi (dosya bulunamadi).
)

echo.
echo ========================================
echo   TUM SERVISLER BASLATILDI!
echo ========================================
echo.
echo Servisler:
echo   - FastAPI:        http://127.0.0.1:8001
echo   - ASP.NET Core:   http://127.0.0.1:5000
echo   - Streamlit:      http://localhost:8501
echo.
echo Kapatmak icin bu pencereyi ve acilan 3 terminali kapatin.
echo.
pause
