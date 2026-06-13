# Devvit Platformu Analizi

Bu doküman, Reddit'in geliştirici platformu Devvit'in kapsamlı bir analizini sunar. ReddTrender projesi için neden Data API'nin gerekli olduğunu ve Devvit'in bu kullanım senaryosuna neden uygun olmadığını açıklar.

## Devvit Nedir?

Devvit, Reddit'in resmi geliştirici platformudur. Topluluk odaklı araçlar, interaktif gönderiler, moderasyon botları ve oyunlar geliştirmek için tasarlanmıştır. Node.js/TypeScript tabanlı, event-driven bir mimari kullanır ve Reddit tarafından ücretsiz olarak barındırılır.

## Temel Özellikler

### Custom Posts (Özel Gönderiler)
Devvit ile subreddit içinde interaktif gönderiler oluşturulabilir. Bu gönderiler butonlar, formlar, görseller ve gerçek zamanlı güncellemeler içerebilir. Kullanıcılar gönderi içinde doğrudan etkileşime girebilir.

### Triggers (Tetikleyiciler)
Devvit uygulamaları, Reddit etkinliklerine otomatik yanıt verebilir. Desteklenen trigger türleri:

- **Gönderi etkinlikleri:** onPostSubmit, onPostCreate, onPostUpdate, onPostDelete, onPostReport, onPostFlairUpdate, onPostNsfwUpdate, onPostSpoilerUpdate
- **Yorum etkinlikleri:** onCommentCreate, onCommentSubmit, onCommentUpdate, onCommentDelete, onCommentReport
- **Moderasyon:** onModAction, onModMail, onAutomoderatorFilterPost, onAutomoderatorFilterComment
- **Uygulama yaşam döngüsü:** onAppInstall, onAppUpgrade

**Önemli kısıt:** Trigger'lar tek seferlik teslimat garantisi vermez — aynı etkinlik birden fazla kez tetiklenebilir.

### Scheduler (Zamanlayıcı)
Devvit Scheduler ile belirli aralıklarla veya belirli zamanlarda işler çalıştırılabilir. PRAW'daki `time.sleep` veya cron job'ların karşılığıdır.

### Redis Veri Saklama
Her subreddit instance'ı için izole bir Redis veritabanı sağlanır. Dosya sistemi yerine Redis kullanılır.

### Realtime Channels
Gerçek zamanlı veri akışı için WebSocket benzeri kanallar kullanılabilir.

### Webviews
Devvit uygulamaları, web tabanlı arayüzler sunabilir.

## Mimari Kısıtlar

### 1. Subreddit Bazlı Kurulum (En Kritik Kısıt)
Devvit uygulamaları **subreddit bazlı** kurulur. Bir uygulama, yalnızca moderatör tarafından kurulduğu subreddit'te çalışır. Cross-subreddit (subredditler arası) veri okuma veya birleştirme mümkün değildir.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  r/technology   │     │  r/programming  │     │  r/worldnews    │
│  ┌───────────┐  │     │  ┌───────────┐  │     │  ┌───────────┐  │
│  │ Devvit App │  │     │  │ Devvit App │  │     │  │ Devvit App │  │
│  │ (izole)    │  │     │  │ (izole)    │  │     │  │ (izole)    │  │
│  └───────────┘  │     │  └───────────┘  │     │  └───────────┘  │
│  Paylaşımsız    │     │  Paylaşımsız    │     │  Paylaşımsız    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ↕                       ↕                       ↕
   Veri birleştirme YOK — her instance bağımsız çalışır
```

### 2. Paylaşımsız Durum (No Shared State)
Subreddit instance'ları arasında veri paylaşımı yoktur. Global Redis kısıtlıdır. Wiki sayfaları gibi dolaylı yöntemlerle senkronizasyon denenebilir ancak pratik ve güvenilir değildir.

### 3. Kısa Ömürlü Handler'lar
Devvit handler'ları hızlı dönmelidir. Uzun süren işlemler, ağır metin analizi veya etkileşimli oturumlar için uygun değildir. Dosya sistemi erişimi yoktur.

### 4. Event-Driven Mimari
Devvit, trigger'lar ve zamanlanmış işler üzerine kuruludur. Kullanıcının isteği üzerine anlık çalışan on-demand (talep üzerine) bir CLI aracıyla uyumsuzdur.

### 5. Kurulum Zorunluluğu
Bir subreddit'te Devvit uygulamasının çalışması için o subreddit'in moderatörünün uygulamayı yüklemesi gerekir. Kendi yönetmediğiniz subreddit'lerde uygulama çalıştıramazsınız.

## Devvit vs Data API Karşılaştırması

| Özellik | Devvit | Data API (OAuth2) |
|---------|--------|-------------------|
| Kapsam | Subreddit bazlı | Global (tüm Reddit) |
| Kurulum | Moderatör onayı gerekli | Kullanıcı kimlik doğrulaması |
| /r/popular erişimi | Yok | Var |
| /best erişimi | Yok | Var |
| /search (global) | Yok | Var |
| Cross-subreddit okuma | Yok | Var |
| Veri birleştirme | Yok | Var |
| On-demand çalışma | Yok (trigger-based) | Var |
| Terminal/CLI desteği | Yok | Var |
| Uzun süreli oturum | Yok | Var |
| Ağır işlem | Kısıtlı | Serbest (rate limit dahilinde) |
| Dosya sistemi | Yok | Serbest (kendi makinenizde) |
| Dil | TypeScript/Node.js | İstediğiniz dil |
| Barındırma | Reddit (ücretsiz) | Kendi makineniz |

## ReddTrender İçin Neden Data API Gerekli?

ReddTrender'ın temel işlevi, birden fazla subreddit'ten trend verilerini toplayıp birleştirilmiş bir görünüm sunmaktır. Bu işlem aşağıdaki adımları gerektirir:

1. **Global okuma:** `/r/popular` ve `/best` endpoint'leri tüm Reddit'i kapsar. Devvit'te bu endpoint'lerin karşılığı yoktur.

2. **Cross-subreddit birleştirme:** 9+ subreddit'ten veri çekip tek bir ısı sıralaması oluşturmak. Devvit'te her instance izole olduğundan bu mimari olarak imkansızdır.

3. **On-demand çalışma:** Kullanıcı terminalde komut çalıştırdığında anlık veri çekmek. Devvit trigger tabanlıdır, kullanıcı tetiklemesiyle çalışmaz.

4. **İnteraktif terminal oturumu:** Rich tablolı çıktı, kelime frekans analizi ve uzun süreli oturum. Devvit handler'ları kısa ömürlüdür ve terminal çıktısı üretemez.

## Devvit'in Uygun Olduğu Senaryolar

Devvit aşağıdaki kullanım senaryoları için mükemmel bir platformdur:

- **Moderasyon botları:** Otomatik spam filtreleme, kural uygulama, kullanıcı uyarı sistemleri
- **İnteraktif oyunlar:** Subreddit içinde çalışan quizler, tahmin oyunları, topluluk etkinlikleri
- **Topluluk araçları:** Flair yönetimi, gönderi şablonları, anketler
- **Bildirim sistemleri:** Belirli olaylarda moderatörleri uyarma
- **Otomatik gönderiler:** Zamanlanmış duyurular, günlük özetler

## Sonuç

Devvit, subreddit kapsamındaki topluluk araçları için tasarlanmış güçlü bir platformdur. Ancak ReddTrender gibi kişisel, cross-subreddit, on-demand veri okuma araçları için temel mimari kısıtları nedeniyle uygun değildir. Data API, bu kullanım senaryosu için tek uygun seçenektir.

---

*Bu analiz, Reddit Developer Platform dokümantasyonu, r/Devvit topluluk tartışmaları ve resmi Devvit migration guide'larından derlenmiştir. Tarih: Haziran 2025.*
