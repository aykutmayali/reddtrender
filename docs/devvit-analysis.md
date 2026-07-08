# Devvit Platformu Analizi

Güncelleme tarihi: 2026-07-08

Bu doküman ReddTrender için iki ayrı geliştirme yolunu ayırır:

1. **Data API / OAuth2:** Cross-subreddit trend izleme, yerel snapshot, dashboard ve pazar araştırması.
2. **Devvit:** Reddit içinde çalışan, review edilebilen, install edilebilen ve para kazanma kanallarına bağlanabilen oyunlar, mod araçları ve community uygulamaları.

ReddTrender'ın mevcut Python CLI mimarisi Data API tarafında doğru konumdadır. Devvit ise ReddTrender'dan çıkan fırsatları Reddit içinde ürüne dönüştürmek için ayrı bir app yüzeyi olarak düşünülmelidir.

## Güncel Devvit Özeti

Devvit, Reddit'in resmi geliştirici platformudur. Uygulamalar Reddit üzerinde yaşar; oyun, interaktif post, subreddit utility ve mod tool geliştirmek için kullanılır.

Güncel resmi dokümanda öne çıkan yapı:

- **Devvit Web:** React, Phaser, Three.js gibi standart web teknolojileriyle webview tabanlı app geliştirme.
- **Client/server ayrımı:** Client webview içinde çalışır; server endpoint'leri Hono, Express veya benzeri Node framework'leriyle yazılabilir.
- **`devvit.json`:** App metadata, post/webview yapılandırması, server entry, permissions, triggers, scheduler, menu ve payments tanımı burada yapılır.
- **Reddit API permission:** Devvit app içinde Reddit API kullanmak için `permissions.reddit = true` açılır; klasik `reddit.com/prefs/apps` client secret yönetimi gerekmez.
- **Redis:** Her app installation/subreddit bağlamında namespaced storage sağlar.
- **Scheduler ve triggers:** Cron benzeri recurring job'lar, one-off job'lar ve Reddit event'lerine yanıt veren handler'lar sağlar.
- **HTTP Fetch:** Server tarafında allowlist edilmiş HTTPS domain'lere istek atılabilir. Client tarafında external fetch yoktur; client kendi `/api/*` endpoint'lerini çağırmalıdır.
- **Payments:** In-App Purchases ile Gold tabanlı ürünler satılabilir; publish öncesi eligibility, verification ve product review gerekir.

Kaynaklar:

- Devvit giriş: https://developers.reddit.com/docs/
- Devvit Web overview: https://developers.reddit.com/docs/capabilities/devvit-web/devvit_web_overview
- Reddit API in Devvit: https://developers.reddit.com/docs/capabilities/server/reddit-api
- Redis storage: https://developers.reddit.com/docs/capabilities/server/redis
- HTTP Fetch: https://developers.reddit.com/docs/capabilities/http-fetch
- Launch guide: https://developers.reddit.com/docs/guides/launch/launch-guide
- Payments overview: https://developers.reddit.com/docs/earn-money/payments/payments_overview
- Developer Funds H1 2026: https://support.reddithelp.com/hc/en-us/articles/27958169342996-Reddit-Developer-Funds-H1-2026-Terms

## ReddTrender İçin Sonuç

ReddTrender'ın amacı birden fazla subreddit ve global Reddit yüzeyinden trend sinyali toplamaktır:

- `/r/popular`
- `r/{subreddit}/hot`
- `r/{subreddit}/rising`
- `r/{subreddit}/top`
- `/search`
- snapshot karşılaştırma
- lokal SQLite geçmişi
- HTML/Markdown/CSV raporlar
- Opportunity Radar ile uygulama fikri skorlama

Bu kullanım **Data API / OAuth2** tarafında kalmalıdır. Devvit'in Reddit API client'ı, app'in kurulu olduğu community bağlamındaki deneyimler için tasarlanmıştır; global cross-subreddit araştırma motoru olarak kullanılmamalıdır.

## Mimari Kısıtlar

### 1. Installation Bazlı State

Devvit Redis verisi her installation için namespaced çalışır. Resmi doküman, cross-community global leaderboard veya aggregated analytics gibi ihtiyaçlar varsa bunu açıkça tasarlamayı ve gerekirse HTTP Fetch ile shared service kullanmayı önerir.

ReddTrender için anlamı:

- Tek makinede global snapshot istiyorsan Data API + SQLite doğru seçim.
- Bir subreddit'e kurulacak mod tool veya oyun istiyorsan Devvit Redis doğru seçim.
- Birden fazla community'den birleşik analitik istiyorsan Devvit tek başına yetmez; external backend ve approval gerekir.

### 2. Serverless Endpoint Limitleri

Devvit Web server endpoint'leri kısa süreli istek/yanıt modeliyle çalışır:

- Max request time: 30 saniye.
- Max payload: 4 MB.
- Max response: 10 MB.
- `fs` ve native external packages desteklenmez.
- Streaming/chunked response ve websockets desteklenmez.

ReddTrender için anlamı:

- Ağır trend analizi, uzun geçmiş taraması ve lokal dosya raporları Python tarafında kalmalı.
- Devvit app, dar ve hızlı user-facing işlevler için kullanılmalı.

### 3. External Fetch Review

HTTP Fetch için domain'ler allowlist/review sürecinden geçer. AI provider tarafında resmi doküman şu anda OpenAI ve Google Gemini domain'lerini allowed provider olarak listeliyor.

ReddTrender için anlamı:

- AI moderation veya summary app yapılacaksa README'de fetch domain gerekçesi yazılmalı.
- Terms ve Privacy Policy gerekir.
- Kişisel domain veya belirsiz veri aktarımı review riskini artırır.

### 4. Data ve Privacy Sınırları

Devvit rules ve Responsible Builder Policy veri minimizasyonu, şeffaflık, consent, silinen içeriklere saygı, credential toplamama ve Reddit data'yı izinsiz commercialize etmeme ilkelerini vurgular.

ReddTrender için anlamı:

- Kullanıcı şifresi veya Reddit credential'ları app içinde üçüncü kişilerden toplanmamalıdır.
- Trend raporları public content attribution ve link-back ile tasarlanmalıdır.
- Reddit data satışı, reklam hedefleme, data brokerlığı veya model eğitimi yapılmamalıdır.

## Devvit vs Data API

| İhtiyaç | En uygun yol |
|---------|--------------|
| Kişisel trend takip CLI'ı | Data API |
| Cross-subreddit snapshot | Data API |
| Lokal SQLite geçmişi | Data API |
| Markdown/CSV/HTML rapor | Data API |
| Subreddit içine kurulan mod tool | Devvit |
| Günlük oyun/trivia/puzzle | Devvit |
| Custom post veya webview UI | Devvit |
| App Directory dağıtımı | Devvit |
| Developer Funds | Devvit |
| In-App Purchases | Devvit |
| Çok community'li global analytics | Hybrid: Devvit + approved backend |

## Para Kazanma Kanalları

### 1. Reddit Developer Funds

H1 2026 terms, Devvit apps için Daily Qualified Engagers ve Qualified Installs eşiklerine göre ödeme kademeleri tanımlar. Üst kademede cumulative payout $167,000 seviyesine kadar listelenmiştir. Programın term, eligibility ve payout kuralları değişebilir; launch öncesi resmi terms tekrar kontrol edilmelidir.

### 2. In-App Purchases

Devvit payments plugin, app içinde premium feature, ek can, item veya exclusive feature satmayı sağlar. Ürünler Reddit Gold ile alınır ve app hesabında Gold birikir. Publish edip satabilmek için eligibility, verification, Earn Terms/Earn Policy ve product review gerekir.

### 3. External SaaS

Subreddit analytics veya market research gibi ürünlerde harici subscription modeli teknik olarak mümkün olabilir, ancak Reddit data'nın ticari kullanımı için yazılı onay gerekebilir. Bu yol review, legal ve privacy açısından Devvit-native oyundan/mod tool'dan daha risklidir.

## Önerilen Ürün Sırası

1. **ReddTrender Opportunity Radar:** Mevcut Data API snapshot'larından hangi kategorilerin ivme aldığını ölç. Bu repo içinde uygulanır.
2. **Devvit Daily Game MVP:** Düşük privacy riski, yüksek engagement, Developer Funds ile uyumlu. Trivia/prediction/leaderboard loop'u.
3. **Devvit Mod Tool MVP:** AI/slop/modqueue veya settings backup gibi net moderator pain point'leri. Distribution için App Directory hedeflenebilir.
4. **Hybrid Analytics:** Ancak ilk traction sonrası. Cross-community aggregation gerekiyorsa approved external backend ve privacy policy ile tasarlanmalı.

## Uygulama Fikirlerinin Platform Fit'i

| Fikir | Fit | Not |
|------|-----|-----|
| AI Content Moderation | Devvit mod tool | OpenAI/Gemini fetch gerekebilir; explainability ve false positive yönetimi kritik. |
| Mod Queue Operations | Devvit mod tool | Moderator permissions, audit trail ve queue prioritization ana değer. |
| Subreddit Analytics | Hybrid | Tek community için Devvit; cross-community için Data API veya approved backend. |
| Daily Community Games | Devvit | En temiz monetization yolu: Developer Funds + IAP. |
| Accessibility/Summary | Devvit utility | AI fetch ve privacy policy gerektirebilir. |
| Settings Backup | Devvit mod tool | AutoMod/wiki/flair/rules snapshot; restore akışı dikkatli tasarlanmalı. |
| Market Research | Data API dashboard | Ticari kullanım ve data handling açısından en fazla onay riski taşıyan kanal. |

## Sonuç

ReddTrender'ı Devvit'e taşımak yerine, ReddTrender'ı **trend ve fırsat keşif motoru** olarak tutmak daha doğru. Para kazanma hedefi için Devvit'te ayrı app'ler geliştirilmeli; ReddTrender bu app'lerin hangi niş ve subredditlerde talep göreceğini ölçen araştırma aracı olmalı.
