# Kaynak Referansları

Bu dosya, mimari dokümanlarda kullanılan ana resmi kaynakları ve hangi karar için referans alındıklarını listeler.

## Reddit ve Devvit Resmi Kaynakları

| Kaynak | Link | Bu Repodaki Karar |
|--------|------|-------------------|
| Devvit ana doküman | https://developers.reddit.com/docs/ | Devvit'in Reddit içinde yaşayan oyun/app/mod tool platformu olarak konumlandırılması. |
| Devvit Web overview | https://developers.reddit.com/docs/capabilities/devvit-web/devvit_web_overview | Devvit app mimarisinin client/server/config şeklinde ayrılması; webview ve `/api/*` endpoint yaklaşımı. |
| Devvit Reddit API overview | https://developers.reddit.com/docs/capabilities/server/reddit-api | Devvit içinde klasik `prefs/apps` API key yönetimi yerine `reddit` permission kullanılması. |
| Devvit Redis | https://developers.reddit.com/docs/capabilities/server/redis | Installation bazlı Redis state, cross-community aggregation için explicit design/shared service gereği. |
| Devvit HTTP Fetch | https://developers.reddit.com/docs/capabilities/http-fetch | External API çağrıları için allowlist, server-side fetch ve AI provider sınırları. |
| Devvit Scheduler | https://developers.reddit.com/docs/capabilities/server/scheduler | Günlük oyun roundları, analytics aggregate ve periodic backup job tasarımları. |
| Launch guide | https://developers.reddit.com/docs/guides/launch/launch-guide | Publish, review, README ve App Directory dağıtım kararları. |
| Payments overview | https://developers.reddit.com/docs/earn-money/payments/payments_overview | In-App Purchases ve Gold tabanlı premium feature stratejisi. |
| Developer Funds H1 2026 | https://support.reddithelp.com/hc/en-us/articles/27958169342996-Reddit-Developer-Funds-H1-2026-Terms | Devvit app monetization hedeflerinin Daily Qualified Engagers ve Qualified Installs ile ilişkilendirilmesi. |
| Responsible Builder Policy | https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy | Data API access, approval, transparency, limits, commercialization ve AI training sınırları. |
| Reddit Developer Terms | https://redditinc.com/policies/developer-terms | Commercial use, rate limits, prohibited uses, user content attribution ve AI training kısıtları. |
| Devvit Rules | https://developers.reddit.com/docs/devvit_rules | Privacy, data minimization, consent, external service ve content-safety kuralları. |

## Yerel Repo Kaynakları

| Dosya | Mimari Rol |
|-------|------------|
| `main.py` | CLI entrypoint ve feature routing. |
| `reddit_client.py` | Data API OAuth2 client ve listing parser. |
| `trends.py` | Anlık trend ve topic hesapları. |
| `storage.py` | SQLite persistence ve snapshot schema. |
| `trend_radar.py` | Snapshot collection, delta, momentum, Markdown/CSV export. |
| `analytics_dashboard.py` | Snapshotlardan standalone HTML dashboard. |
| `opportunity_radar.py` | Snapshotlardan Reddit/Devvit ürün fırsatı skorlama. |
| `docs/devvit-analysis.md` | Data API ile Devvit ayrımı ve monetization değerlendirmesi. |
| `docs/reddit-app-opportunities.md` | Uygulama fırsatları araştırması ve Opportunity Radar bağlantısı. |

## Kaynak Kullanım Notları

- Kaynaklar 2026-07-08 tarihinde kontrol edildi.
- Reddit ve Devvit policy/dokümanları değişebilir; launch, payment veya commercial use öncesi tekrar doğrulanmalıdır.
- Bu repo içindeki dokümanlar hukuki tavsiye değildir; ürünleşme kararlarında resmi terms ve gerekiyorsa yazılı Reddit onayı esas alınmalıdır.
