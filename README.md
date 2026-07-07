# ReddTrender

Reddit API'den trend bilgilerini çeken ve terminalde görsel olarak sunan Python tabanlı CLI uygulaması.

## Reddit Responsible Builder Policy (Yeni Doküman)

Reddit, 2025 yılında **Responsible Builder Policy** adını verdiği yeni bir geliştirici politikası yayınladı. Bu politika, API erişimi için ön onay sürecini zorunlu kılmakta ve daha önce açık olan self-service uygulama oluşturma sistemini kısıtlamaktadır.

### Reddit'in Onayladığı Uygulama Türleri

Reddit, Responsible Builder Policy kapsamında aşağıdaki kategorilerde uygulama onayı vermektedir:

**Mod Araçları (Mod Tools):** Subreddit moderasyonunu destekleyen botlar, spam filtreleri, otomatik kurallar uygulayan araçlar ve moderatör panelleri gibi topluluk yönetimine doğrudan katkı sağlayan uygulamalar.

**Uygulama Şeffaflığı (App Transparency):** Reddit deneyimini geliştiren araçlar, kullanıcı etkileşimini artıran uygulamalar ve Reddit topluluğuna fayda sağlayan okuma/yazma araçları.

**Araştırma ve Kişisel Kullanım:** Akademik araştırma projeleri, kişisel kullanım amaçlı scriptler, veri analizi araçları ve Reddit topluluğuna değer katan non-profit projeler.

### Reddit'in Onaylamadığı Uygulama Türleri

Politika gereği aşağıdaki türde uygulamalar genellikle reddedilmektedir: ticari veri kazıma (scraping) araçları, kullanıcı gizliliğini ihlal eden uygulamalar, topluluk sağlığına zarar veren botlar, izinsiz reklam/promosyon araçları ve Reddit verilerini üçüncü taraflarla paylaşan servisler.

### Onay Süreci

Reddit'in yeni sürecinde self-service uygulama oluşturma kapatılmıştır. Geliştiriciler, API erişimi için destek formları aracılığıyla başvuruda bulunmalıdır. Başvurular 7 gün içinde sonuçlanmayı hedefler. Onaylanan uygulamalar, bot kimliğini user-agent ile açıkça belirtmelidir.

## API Key Oluşturma Adımları

> **Not:** Reddit'in Responsible Builder Policy'si gereği, `/prefs/apps` sayfasında doğrudan uygulama oluşturamazsınız. Önce destek talebi (support ticket) gönderip onay almanız gerekir.

### BÖLÜM A: Onay Başvurusu (Zorunlu İlk Adım)

#### 1. Destek Talebi Formunu Açın
Reddit geliştirici destek formuna gidin:
[https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14867328473236](https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14867328473236)

#### 2. Form Türünü Seçin
- **Developer** — Uygulama/bot geliştirmek için (bu proje için uygun olan)
- **Researcher** — Akademik araştırma için
- **Moderator** — Subreddit moderasyon araçları için

#### 3. Başvurunuzu Detaylı Yazın
Reddit ekibi belirsiz talepleri reddeder. Başvurunuzda mutlaka şunları belirtin:

- Uygulamanızın adı ve amacı
- Hangi API endpointlerini kullanacaksınız
- Verileri nasıl kullanacağınız (saklanacak mı, paylaşılacak mı?)
- Uygulama türü (Script / Web App / Installed App)
- Ticari mi, kişisel mi
- Reddit topluluğuna katkısı

#### 4. Onay Bekleyin
Hedeflenen yanıt süresi ~7 iş günü, ancak gerçek süre 1-4 hafta arası değişebilir. Onay e-postası alana kadar uygulama oluşturamazsınız.

#### 5. Onay Sonrası
Onaylanırsa `/prefs/apps` sayfasında uygulama oluşturmanıza izin verilecektir. Reddedilirse talebi detaylandırarak tekrar başvurabilirsiniz.

<details>
<summary><strong>Örnek Başvuru Mesajı (İngilizce)</strong></summary>

```
Subject: API Access Request — ReddTrender (Personal Script App)

Hello Reddit Developer Support,

I would like to request API access for a personal-use script application
called "ReddTrender."

Purpose:
A local CLI tool that reads publicly available trending posts across
subreddits to help me stay informed about topics I care about on Reddit.
It is a personal daily news digest tool — nothing more.

Endpoints I plan to use:
- GET /r/popular
- GET /r/{subreddit}/hot
- GET /r/{subreddit}/rising
- GET /r/{subreddit}/top

Data handling:
- All data is read-only (no posting, commenting, or writing).
- Data is displayed only in my local terminal session.
- Nothing is stored in a database, shared with third parties,
  or redistributed in any form.
- No user data is collected.

Application type: Script app (personal use, single developer account)
Commercial use: No — entirely non-commercial, personal use only.
Community impact: Zero negative impact. Read-only, no automated
interaction with users or communities.

I will comply with all rate limits and Responsible Builder Policy
requirements, including proper User-Agent identification.

Thank you for your time.

Best regards,
u/your_reddit_username
```

</details>

### BÖLÜM B: Uygulama Oluşturma (Onay Aldıktan Sonra)

#### 6. Reddit Hesabınıza Giriş Yapın
Aktif bir Reddit hesabına sahip olmanız gerekir. Yeni hesaplar yerine, en az birkaç aylık geçmişi olan ve karma puanı bulunan hesaplar tercih edilir.

#### 7. Uygulama Kaydı Oluşturun
Onay aldıktan sonra [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) adresine gidin ve **"create another app..."** butonuna tıklayın.

#### 8. Uygulama Türünü Seçin
Bu proje için **"script"** türünü seçin. Script uygulamaları kişisel kullanım içindir ve OAuth2 password grant akışını kullanır.

| Tür | Açıklama | Auth Akışı |
|-----|----------|------------|
| **script** | Kişisel bot/scriptler | Password Grant |
| **web app** | Kullanıcı adına çalışan web uygulamaları | Authorization Code |
| **installed app** | Masaüstü/mobil uygulamalar | Authorization Code / Implicit |

#### 9. Uygulama Bilgilerini Doldurun
- **name:** Uygulamanızın adı (örn: `ReddTrender`)
- **description:** Kısa açıklama
- **about url:** Projenizin web adresi (opsiyonel)
- **redirect uri:** `http://localhost:8080` (script tipi için zorunlu değil ancak form gereği)

#### 10. Kimlik Bilgilerini Kaydedin
Uygulama oluşturulduktan sonra aşağıdaki bilgileri not edin:
- **client_id:** Uygulama adının altında gösterilir
- **client_secret:** "secret" olarak etiketlenmiştir

#### 11. Ortam Değişkenlerini Yapılandırın
Proje kök dizininde `.env` dosyası oluşturun ve bilgileri girin:

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=python:reddtrender:v1.0.0 (by /u/your_username)
```

> **Önemli:** User-Agent alanı Reddit kuralları gereği benzersiz ve tanımlayıcı olmalıdır. Format: `<platform>:<app_id>:v<version> (by /u/<username>)`

## Kurulum

```bash
# Projeyi klonlayın
git clone <repo-url>
cd reddtrender

# Sanal ortam oluşturun (önerilir)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# .env dosyasını yapılandırın (yukarıdaki adımları izleyin)
cp .env.example .env
```

## Kullanım

```bash
# Genel günlük trend özeti
python main.py

# Popüler gönderiler
python main.py --hot

# Yükselişte olan gönderiler (viral analiz ile)
python main.py --rising

# Günün en çok oy alanları
python main.py --top

# Haftanın en çok oy alanları
python main.py --top --time week

# Varsayılan subreddit trend analizi
python main.py --subreddits

# Özel subreddit analizi
python main.py --subreddits technology,programming,science

# Sıcak konular ve kelime analizi
python main.py --topics

# Reddit'te arama
python main.py --search "python"

# Belirli subreddit'te arama
python main.py --search "machine learning" --sub learnprogramming
```

## Trend Radar (Yerel Snapshot ve Raporlama)

Trend Radar, Reddit'ten alınan gönderileri yerel SQLite veritabanına kaydeder ve
sonraki çalıştırmalarda önceki snapshot ile karşılaştırarak hangi konuların
hızlandığını gösterir.

```bash
# Güncel Reddit verisini yerel snapshot olarak kaydet
python main.py --snapshot

# Son snapshot üzerinden momentum raporu göster
python main.py --radar

# Tek komutta snapshot al, radar göster ve Markdown raporu üret
python main.py --snapshot --radar --export markdown

# CSV raporu üret
python main.py --radar --export csv

# Belirli subreddit listesini takip et
python main.py --snapshot --subreddits technology,programming,artificial

# Keyword alarmlarını özelleştir
python main.py --snapshot --keywords "ai,openai,privacy,security"

# Snapshot geçmişini göster
python main.py --history

# Son snapshot'ın keyword alarmlarını göster
python main.py --alerts
```

## Subreddit Analytics Dashboard

Dashboard, Trend Radar snapshot verilerini okunabilir bir HTML panele dönüştürür.
Ek sunucu veya web framework gerektirmez; çıktı `reports/` içinde tek HTML dosyası
olarak oluşur.

```bash
# Son snapshot'tan HTML dashboard üret
python main.py --dashboard

# Snapshot al ve aynı çalışmada dashboard üret
python main.py --snapshot --dashboard

# Dashboard'da son 12 snapshot'ı kullan
python main.py --dashboard --dashboard-history 12

# Belirli snapshot için dashboard üret
python main.py --dashboard --snapshot-id 3

# Çıktı dosyasını kendin seç
python main.py --dashboard --dashboard-output reports/subreddit-dashboard.html
```

Dashboard bölümleri:

- Genel KPI'lar: gönderi sayısı, takip edilen subreddit sayısı, toplam ısı, keyword alarmı.
- Subreddit ısı liderleri ve önceki snapshot'a göre farklar.
- Snapshot geçmişinden ısı çizgisi.
- Keyword alarm yoğunluğu.
- Momentum gönderileri.
- Operasyon notları ve kısa aksiyon önerileri.

### Trend Radar Mantığı

- `--snapshot`, `/r/popular`, `r/popular/rising`, `r/popular/top?t=day` ve seçili subreddit'lerin hot akışını toplar.
- Veriler `data/reddtrender.db` içinde saklanır.
- `--radar`, son snapshot ile bir önceki snapshot'ı karşılaştırır.
- Aynı gönderiler için skor ve yorum farkı hesaplanır.
- Yeni gönderiler yaşına göre normalize edilerek momentum skoruna dahil edilir.
- Keyword eşleşmeleri snapshot sırasında kaydedilir.
- `--export markdown` ve `--export csv` çıktıları `reports/` klasörüne yazılır.

### Trend Radar Ortam Değişkenleri

```env
REDDTRENDER_DATA_DIR=data
REDDTRENDER_REPORT_DIR=reports
REDDTRENDER_KEYWORDS=ai,openai,python,startup,security,privacy,reddit
```

## Proje Yapısı

```
reddtrender/
├── main.py              # CLI giriş noktası ve argüman yönetimi
├── reddit_client.py     # Reddit OAuth2 API istemcisi
├── trends.py            # Trend analiz ve veri işleme
├── storage.py           # SQLite snapshot saklama katmanı
├── trend_radar.py       # Snapshot karşılaştırma ve rapor export servisi
├── analytics_dashboard.py # HTML dashboard üretim servisi
├── config.py            # Yapılandırma ve ortam değişkenleri
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Örnek ortam değişkenleri
├── data/                # Yerel SQLite veritabanı (git'e eklenmez)
├── reports/             # Markdown/CSV rapor çıktıları (git'e eklenmez)
└── README.md            # Bu dosya
```

## API Endpointleri

Bu projenin kullandığı Reddit API endpointleri:

| Endpoint | Açıklama |
|----------|----------|
| `GET /r/popular` | Reddit genelindeki popüler gönderiler |
| `GET /r/{subreddit}/hot` | Subreddit'in popüler gönderileri |
| `GET /r/{subreddit}/rising` | Yükselişte olan gönderiler |
| `GET /r/{subreddit}/top?t={time}` | Zaman filtreli en çok oy alanlar |
| `GET /best` | Kullanıcıya özel en iyi gönderiler |
| `GET /search?q={query}` | Reddit arama |

## Rate Limit

Reddit ücretsiz katman için **dakikada 100 istek** sınırı uygular. Uygulama bu sınırı otomatik olarak takip eder:

- `X-Ratelimit-Remaining` başlığı ile kalan istek sayısı izlenir
- Sınır yaklaştığında otomatik bekleme yapılır
- 429 hatası durumunda exponential backoff uygulanır

## Sorun Giderme

**Kimlik doğrulama hatası:** `.env` dosyasındaki bilgileri kontrol edin. Client ID ve secret'ın doğru olduğundan emin olun.

**403 Forbidden:** User-Agent alanının doğru formatta olduğunu kontrol edin. Reddit, benzersiz user-agent gerektirir.

**429 Too Many Requests:** Rate limit aşılmış demektir. Uygulama otomatik olarak bekleyecektir, manuel müdahale gerekmez.

## Lisans

MIT
