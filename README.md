# NASDAQ Financial RAG Assistant

Bu proje, Microsoft AI Innovators Summer Internship kapsamında geliştirilen Türkçe arayüzlü bir finansal RAG asistanıdır.

Proje; seçili NASDAQ şirketlerinin SEC 10-K raporları üzerinde çalışarak kullanıcı sorularına doküman temelli yanıtlar üretmeyi amaçlar. Sistem, kullanıcı sorusuyla en ilgili rapor parçalarını getirir ve cevabın hangi filing, section ve source chunk üzerinden üretildiğini gösterir.

> Bu proje geliştirme aşamasındadır. Günlük commitlerle adım adım ilerletilmektedir.

## Proje Amacı

Finansal raporlar uzun, teknik ve manuel olarak incelenmesi zaman alan dokümanlardır. Bu proje, seçili NASDAQ şirketlerinin SEC 10-K raporlarını daha hızlı analiz edebilmek için RAG tabanlı bir araştırma asistanı geliştirmeyi hedefler.

Amaç, genel bir doküman chatbotu geliştirmek yerine gerçek finansal dokümanlar üzerinde çalışan, cevaplarını ilgili rapor bölümleriyle destekleyen bir yerel RAG uygulaması oluşturmaktır.

## Kullanılan Şirketler

İlk sürümde aşağıdaki NASDAQ şirketleriyle çalışılması planlanmaktadır:

* AAPL — Apple Inc.
* MSFT — Microsoft Corporation
* NVDA — NVIDIA Corporation
* AMZN — Amazon.com, Inc.
* GOOGL — Alphabet Inc.

## Kullanılan Veri Kaynağı

Projede SEC EDGAR üzerinden alınan 10-K raporları kullanılacaktır.

İlk sürümde her şirket için en güncel 10-K raporu üzerinde çalışılması hedeflenmektedir.

## Temel Özellikler

* SEC 10-K raporlarını indirme ve işleme
* Rapor metinlerini chunk yapısına ayırma
* Embedding üretimi
* Vector search ile ilgili doküman parçalarını getirme
* RAG tabanlı cevap üretimi
* Türkçe Streamlit dark theme arayüz
* Cevap altında filing type, section, chunk ve skor bilgisi gösterimi

## Kullanılan Teknolojiler

* Python
* Streamlit
* Microsoft Foundry Local
* SEC EDGAR
* RAG
* Embeddings
* Vector Search

## Sistem Akışı

```text
SEC EDGAR
↓
10-K Raporları
↓
Metin Temizleme
↓
Chunking
↓
Embedding Üretimi
↓
Vector Search
↓
RAG Cevabı
↓
Kaynak Chunk Gösterimi
```

## Örnek Sorular

```text
NVIDIA son 10-K raporunda yapay zeka ile ilgili hangi risklerden bahsediyor?
```

```text
Apple son 10-K raporunda tedarik zinciriyle ilgili hangi riskleri açıklıyor?
```

```text
Microsoft son 10-K raporunda bulut hizmetleri ve rekabet hakkında ne söylüyor?
```

## Geliştirme Planı

### V1

* SEC 10-K raporları
* RAG cevap üretimi
* Türkçe Streamlit arayüz
* Cevap altında source chunk gösterimi

### V2

* ASP.NET Core Web API
* Piyasa verisi katmanı
* PostgreSQL + pgvector
* 10-Q raporları
* Power BI dashboard

## Yasal Uyarı

Bu proje yatırım tavsiyesi vermez. Yalnızca SEC raporları üzerinden araştırma amaçlı özetleme ve doküman temelli bilgi sunumu yapar.
