# ADR-001: Orkestrasyon Framework Değerlendirmesi

**Durum:** Kabul edildi  
**Tarih:** 18 Temmuz 2026  
**Kapsam:** NASDAQ Financial RAG Assistant

## Bağlam

NASDAQ Financial RAG Assistant şu anda aşağıdaki deterministik servis hattını kullanmaktadır:

```text
Streamlit
    ↓
ASP.NET Core Web API
    ↓
FastAPI AI Servisi
    ↓
PostgreSQL + pgvector
    ↓
Microsoft Foundry Local
    ↓
Cevap Kalite Kapısı
    ↓
Gerekirse Kontrollü Fallback
```

Sistemin temel amacı, seçili NASDAQ şirketlerinin SEC 10-K raporları üzerinden kaynak temelli ve doğrulanabilir Türkçe cevaplar üretmektir.

Mevcut akışta:

- Kullanıcı girdisi belirli bir API endpointi üzerinden alınır.
- Retrieval adımı PostgreSQL ve pgvector ile gerçekleştirilir.
- En alakalı doküman parçaları modele bağlam olarak iletilir.
- Cevap kalite kurallarıyla doğrulanır.
- Gerekirse kontrollü fallback cevabı üretilir.
- Kaynaklar, section bilgileri, chunk kimlikleri ve skorlar kullanıcıya gösterilir.

Bu nedenle mevcut işlem sırası açık, sınırları belirli ve test edilebilirdir.

## Değerlendirilen Seçenekler

### 1. Mevcut deterministik RAG mimarisini korumak

Mevcut servis sorumlulukları değiştirilmeden korunur.

Avantajları:

- Çalışan uçtan uca akış bozulmaz.
- Retrieval ve cevap üretim adımları açık biçimde izlenebilir.
- Hata ayıklama daha kolaydır.
- Kalite kapısı ve kontrollü fallback mekanizması korunur.
- Yeni bir framework bağımlılığı ve öğrenme maliyeti oluşmaz.
- API sözleşmeleri değişmeden kalır.

Dezavantajları:

- Gelecekte açık uçlu araç seçimi gerekirse yeni bir orchestration katmanı tasarlanması gerekebilir.
- Çoklu ajan senaryoları için mevcut akış tek başına yeterli olmayabilir.

### 2. Semantic Kernel eklemek

Semantic Kernel; model servisleri, plugin yapıları, fonksiyon çağrıları ve agent tabanlı uygulamalar için kullanılabilir.

Ancak bu projede Semantic Kernel eklenmesi:

- Mevcut FastAPI retrieval ve cevap üretim akışını tekrar eden bir katman oluşturabilir.
- ASP.NET Core ile Python servisleri arasına ek soyutlama ekleyebilir.
- Çalışan kalite ve fallback mekanizmasının yeniden tasarlanmasını gerektirebilir.
- Mevcut kapsam için ölçülebilir bir ürün faydası sağlamadan bakım yükünü artırabilir.

Microsoft, Semantic Kernel agent uygulamalarından Microsoft Agent Framework'e geçiş için resmi migration rehberi yayımlamaktadır. Bu nedenle yeni bir agent orchestration yatırımı yapılacaksa yalnızca Semantic Kernel eklemek yerine Agent Framework değerlendirilmelidir.

### 3. Microsoft Agent Framework eklemek

Microsoft Agent Framework; Python ve .NET üzerinde production-grade agent ve multi-agent workflow'ları geliştirmek için tasarlanmıştır.

Framework özellikle şu ihtiyaçlarda güçlüdür:

- Tek prompt veya stateless chat döngüsünün ötesinde orchestration
- Graph tabanlı sequential, concurrent, handoff ve group collaboration akışları
- Session ve durum yönetimi
- Checkpointing ve yeniden başlatılabilir workflow'lar
- Human-in-the-loop süreçleri
- Middleware ve gözlemlenebilirlik
- Çoklu ajan koordinasyonu
- Dinamik araç seçimi

Microsoft Agent Framework, Semantic Kernel ve AutoGen'in devamı olarak konumlandırılmıştır ve her iki ekosistemin agent özelliklerini ortak bir yapıda birleştirmektedir.

Ancak mevcut NASDAQ Financial RAG Assistant:

- Çoklu ajan kullanmamaktadır.
- Açık uçlu görev planlaması yapmamaktadır.
- Modelin bağımsız araç seçmesine ihtiyaç duymamaktadır.
- Uzun süreli agent session'ları tutmamaktadır.
- Human-in-the-loop onay akışı gerektirmemektedir.
- Graph tabanlı dinamik workflow çalıştırmamaktadır.

Bu nedenle Agent Framework entegrasyonu bugünkü kapsam için gereksiz karmaşıklık oluşturacaktır.

## Karar

Mevcut sürümde:

```text
Semantic Kernel entegre edilmeyecek.
Microsoft Agent Framework entegre edilmeyecek.
Mevcut deterministik RAG mimarisi korunacak.
```

Bu kararın temel gerekçeleri:

1. Mevcut işlem akışı belirli, kontrollü ve test edilebilirdir.
2. Agent tabanlı açık uçlu planlama ihtiyacı bulunmamaktadır.
3. Retrieval, cevap üretimi ve kalite kontrolü mevcut servislerde ayrılmıştır.
4. Ek framework bağımlılığı ürün değerinden daha fazla bakım yükü oluşturacaktır.
5. Projenin amacı otonom finansal ajan değil, kaynak temelli finansal araştırma asistanıdır.
6. Mevcut API endpointleri ve kalite raporlama sistemi korunmalıdır.

## Sonuçlar

### Olumlu Sonuçlar

- Çalışan mimari korunur.
- Teknik borç artmaz.
- Servis sınırları açık kalır.
- Kalite değerlendirme sistemi değişmeden çalışır.
- Demo ve proje sunumu için mimari daha anlaşılır kalır.
- Gelecekte agent denemesi yapılırsa mevcut RAG hattı güvenilir temel olarak kullanılabilir.

### Kabul Edilen Sınırlamalar

- Sistem otonom araç seçimi yapmaz.
- Çoklu uzman ajan koordinasyonu bulunmaz.
- Uzun süreli workflow state'i tutulmaz.
- Human-in-the-loop süreçleri bulunmaz.
- Agent tabanlı araştırma planlaması yapılmaz.

Bu sınırlamalar mevcut ürün kapsamı için kabul edilebilir durumdadır.

## Yeniden Değerlendirme Koşulları

Aşağıdaki ihtiyaçlardan biri gerçek ürün gereksinimi hâline gelirse Microsoft Agent Framework yeniden değerlendirilecektir:

- SEC raporları, piyasa verileri ve haberler arasında dinamik kaynak seçimi
- Kullanıcı isteğine göre farklı araçları çağıran araştırma ajanı
- Risk, şirket ve karşılaştırma analizi için uzman ajanlar
- Çok adımlı ve uzun süreli araştırma workflow'ları
- Checkpointing ve işlem devam ettirme
- Human-in-the-loop onay mekanizması
- Session tabanlı uzun süreli kullanıcı bağlamı
- Merkezi telemetry ve agent gözlemlenebilirliği
- Graph tabanlı multi-agent orchestration

## Olası Gelecek Denemesi

İleride deneysel bir agent çalışması yapılırsa mevcut endpoint değiştirilmemelidir.

```text
Mevcut ve kararlı endpoint:
POST /api/rag/ask

Olası deneysel endpoint:
POST /api/agent/research
```

Deneysel çalışma:

- Ayrı bir feature branch üzerinde yürütülmeli
- Mevcut RAG endpointini değiştirmemeli
- Aynı kalite kapısıyla karşılaştırılmalı
- Latency, doğruluk, kaynak kalitesi ve bakım maliyeti açısından ölçülmeli
- Başarısız olduğunda mevcut RAG hattını fallback olarak korumalıdır

## Nihai Değerlendirme

Mevcut teknik kapsam için en doğru karar, çalışan RAG mimarisini korumak ve agent framework entegrasyonunu gerçek bir orchestration ihtiyacı ortaya çıkana kadar ertelemektir.

Bu yaklaşım framework kullanımını amaç hâline getirmek yerine, mimari kararları somut ürün gereksinimlerine bağlar.

## Resmî Kaynaklar

- Microsoft Agent Framework Overview  
  https://learn.microsoft.com/en-us/agent-framework/overview/

- Microsoft Agent Framework GitHub Repository  
  https://github.com/microsoft/agent-framework

- Semantic Kernel to Microsoft Agent Framework Migration Guide  
  https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/

- AutoGen to Microsoft Agent Framework Migration Guide  
  https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/
