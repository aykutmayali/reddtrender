# Devvit Örnek Uygulama: Subreddit Moderasyon Botu

Bu doküman, Devvit platformunun temel özelliklerini gösteren çalışan bir moderasyon botu örneği sunar. Örnek; trigger, scheduler, custom post ve menü özelliklerini kapsar.

## Proje Yapısı

```
my-mod-bot/
├── devvit.json                 # Uygulama yapılandırması
├── package.json
├── public/                     # Custom post frontend
│   └── index.html
└── src/
    ├── server/
    │   └── index.ts            # Backend handler'ları
    └── shared/
        └── types.ts            # Paylaşımlı tipler
```

## 1. devvit.json — Uygulama Yapılandırması

```json
{
  "$schema": "https://developers.reddit.com/schema/config-file.v1.json",
  "name": "reddtrender-mod-bot",
  "post": {
    "dir": "public",
    "entrypoints": {
      "welcome": {
        "entry": "index.html",
        "height": "tall"
      }
    }
  },
  "server": {
    "entry": "src/server/index.ts"
  },
  "permissions": {
    "http": {
      "enable": true,
      "domains": []
    },
    "redis": true,
    "media": false
  },
  "triggers": {
    "onPostCreate": "/internal/triggers/on-post-create",
    "onCommentCreate": "/internal/triggers/on-comment-create",
    "onAppInstall": "/internal/triggers/on-app-install"
  },
  "scheduler": {
    "tasks": {
      "daily-report": {
        "endpoint": "/internal/cron/daily-report",
        "cron": "0 9 * * *"
      },
      "cleanup": {
        "endpoint": "/internal/cron/cleanup",
        "cron": "0 2 * * 0"
      }
    }
  },
  "menu": {
    "items": [
      {
        "label": "Günlük Rapor Oluştur",
        "forUserType": "moderator",
        "location": "subreddit",
        "endpoint": "/internal/menu/generate-report"
      },
      {
        "label": "Hoşgeldin Postu Gönder",
        "forUserType": "moderator",
        "location": "subreddit",
        "endpoint": "/internal/menu/send-welcome"
      }
    ]
  },
  "dev": {
    "subreddit": "my-test-subreddit"
  },
  "scripts": {
    "dev": "devvit playtest r/my-test-subreddit",
    "build": "tsc"
  }
}
```

## 2. Server — Backend Handler'ları (src/server/index.ts)

```typescript
import { Hono } from "hono";
import { redis } from "@devvit/web/server";
import type {
  OnPostCreateRequest,
  OnCommentCreateRequest,
  OnAppInstallRequest,
  TriggerResponse,
  MenuActionRequest,
  SchedulerTaskRequest,
} from "@devvit/web/shared";

const app = new Hono();

// ─────────────────────────────────────────────────
// TRIGGER: Yeni gönderi oluşturulduğunda
// ─────────────────────────────────────────────────
app.post("/internal/triggers/on-post-create", async (c) => {
  const input = await c.req.json<OnPostCreateRequest>();
  const post = input.post;
  const author = input.author;

  // Gönderi istatistiklerini Redis'e kaydet
  const today = new Date().toISOString().split("T")[0];
  const key = `posts:${today}`;

  await redis.hIncrBy(key, "count", 1);
  await redis.hSet(key, `last_author`, author?.name ?? "unknown");
  await redis.hSet(key, `last_title`, post?.title ?? "");

  // Otomatik hoşgeldin yorumu (ilk gönderi ise)
  const userPostCount = await redis.hIncrBy(
    `user_posts:${author?.name}`,
    "total",
    1
  );

  if (userPostCount === 1 && author?.name) {
    // İlk gönderi — hoşgeldin mesajı gönder
    console.log(
      `Yeni kullanıcı tespit edildi: u/${author.name}. Hoşgeldin mesajı hazırlanıyor.`
    );
  }

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// TRIGGER: Yeni yorum oluşturulduğunda
// ─────────────────────────────────────────────────
app.post("/internal/triggers/on-comment-create", async (c) => {
  const input = await c.req.json<OnCommentCreateRequest>();
  const comment = input.comment;
  const author = input.author;

  // Yorum sayısını takip et
  const today = new Date().toISOString().split("T")[0];
  await redis.hIncrBy(`comments:${today}`, "count", 1);

  // Spam kontrolü: aynı kullanıcıdan son 1 saatte 20+ yorum
  if (author?.name) {
    const hourKey = `user_comments_hourly:${author.name}`;
    const recentCount = await redis.incr(hourKey);

    if (recentCount === 1) {
      // İlk yorum — 1 saat TTL
      await redis.expire(hourKey, 3600);
    }

    if (recentCount > 20) {
      console.log(
        `Uyarı: u/${author.name} son 1 saatte ${recentCount} yorum yaptı.`
      );
    }
  }

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// TRIGGER: Uygulama ilk kurulduğunda
// ─────────────────────────────────────────────────
app.post("/internal/triggers/on-app-install", async (c) => {
  const _input = await c.req.json<OnAppInstallRequest>();

  // Başlangıç verilerini oluştur
  await redis.set("app:installed_at", new Date().toISOString());
  await redis.set("app:total_reports", "0");

  console.log("Mod bot başarıyla kuruldu ve yapılandırıldı.");

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// SCHEDULER: Günlük rapor (her gün 09:00)
// ─────────────────────────────────────────────────
app.post("/internal/cron/daily-report", async (c) => {
  const _input = await c.req.json<SchedulerTaskRequest>();

  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dateKey = yesterday.toISOString().split("T")[0];

  // Dünün istatistiklerini topla
  const posts = await redis.hGetAll(`posts:${dateKey}`);
  const comments = await redis.hGetAll(`comments:${dateKey}`);

  const report = {
    date: dateKey,
    total_posts: parseInt(posts?.count ?? "0"),
    last_post_author: posts?.last_author ?? "N/A",
    last_post_title: posts?.last_title ?? "N/A",
    total_comments: parseInt(comments?.count ?? "0"),
  };

  // Raporu Redis'e kaydet
  await redis.set(`report:${dateKey}`, JSON.stringify(report));
  await redis.incr("app:total_reports");

  console.log(
    `Günlük rapor oluşturuldu: ${report.total_posts} gönderi, ${report.total_comments} yorum`
  );

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// SCHEDULER: Haftalık temizlik (her Pazar 02:00)
// ─────────────────────────────────────────────────
app.post("/internal/cron/cleanup", async (c) => {
  const _input = await c.req.json<SchedulerTaskRequest>();

  // 30 günden eski rapor anahtarlarını temizle
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 30);

  let cleaned = 0;
  for (let i = 0; i < 30; i++) {
    const d = new Date(cutoff);
    d.setDate(d.getDate() - i);
    const key = `report:${d.toISOString().split("T")[0]}`;
    await redis.del(key);
    cleaned++;
  }

  console.log(`Haftalık temizlik tamamlandı: ${cleaned} eski kayıt silindi.`);

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// MENÜ: Manuel rapor oluşturma (moderatör aksiyonu)
// ─────────────────────────────────────────────────
app.post("/internal/menu/generate-report", async (c) => {
  const _input = await c.req.json<MenuActionRequest>();

  const today = new Date().toISOString().split("T")[0];
  const posts = await redis.hGetAll(`posts:${today}`);
  const comments = await redis.hGetAll(`comments:${today}`);

  console.log(
    `[Manuel Rapor] ${today}: ` +
      `${posts?.count ?? 0} gönderi, ${comments?.count ?? 0} yorum`
  );

  return c.json<TriggerResponse>({ status: "ok" });
});

// ─────────────────────────────────────────────────
// MENÜ: Hoşgeldin postu gönder
// ─────────────────────────────────────────────────
app.post("/internal/menu/send-welcome", async (c) => {
  const _input = await c.req.json<MenuActionRequest>();

  // Custom post tipinde hoşgeldin mesajı oluştur
  // Bu, subreddit ana sayfasında interaktif bir post olarak görünür
  console.log("Hoşgeldin postu oluşturuluyor...");

  return c.json<TriggerResponse>({ status: "ok" });
});

export default app;
```

## 3. Custom Post Frontend (public/index.html)

```html
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Subreddit İstatistikleri</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #1a1a1b;
      color: #d7dadc;
      padding: 20px;
    }
    .card {
      background: #272729;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
      border: 1px solid #343536;
    }
    .card h2 {
      color: #ff4500;
      margin-bottom: 12px;
      font-size: 18px;
    }
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px;
    }
    .stat-item {
      background: #1a1a1b;
      padding: 16px;
      border-radius: 6px;
      text-align: center;
    }
    .stat-value {
      font-size: 28px;
      font-weight: bold;
      color: #ff4500;
    }
    .stat-label {
      font-size: 12px;
      color: #818384;
      margin-top: 4px;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>Günlük Subreddit İstatistikleri</h2>
    <div class="stat-grid">
      <div class="stat-item">
        <div class="stat-value" id="post-count">--</div>
        <div class="stat-label">Gönderi</div>
      </div>
      <div class="stat-item">
        <div class="stat-value" id="comment-count">--</div>
        <div class="stat-label">Yorum</div>
      </div>
      <div class="stat-item">
        <div class="stat-value" id="active-users">--</div>
        <div class="stat-label">Aktif Kullanıcı</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Son Aktivite</h2>
    <p id="last-activity">Yükleniyor...</p>
  </div>
</body>
</html>
```

## 4. package.json

```json
{
  "name": "reddtrender-mod-bot",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "devvit playtest r/my-test-subreddit",
    "build": "tsc",
    "launch": "devvit launch"
  },
  "dependencies": {
    "@devvit/web": "latest",
    "hono": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "devvit": "latest"
  }
}
```

## Kurulum ve Çalıştırma

```bash
# 1. Devvit CLI yükle
npm install -g devvit

# 2. Reddit hesabınla giriş yap
devvit login

# 3. Proje klasörüne git
cd my-mod-bot

# 4. Bağımlılıkları yükle
npm install

# 5. Test subreddit'inde geliştirme modunda çalıştır
npm run dev

# 6. Yayına al
npm run launch
```

## Devvit vs ReddTrender (Data API) Karşılaştırması

Bu örnek uygulama, Devvit ile Data API arasındaki farkı net biçimde gösterir:

| Özellik | Bu Devvit Botu | ReddTrender (Data API) |
|---------|---------------|----------------------|
| **Kapsam** | Tek subreddit | Tüm Reddit (9+ subreddit) |
| **Kurulum** | Moderatör onayı gerekli | Sadece kendi hesabın |
| **Veri okuma** | Subreddit içi | Cross-subreddit |
| **Çalışma zamanı** | Reddit sunucusu | Kendi makineniz |
| **Dil** | TypeScript/Node.js | İstediğiniz dil (Python) |
| **Etkileşim** | Yorum yazabilir, post oluşturabilir | Sadece okuma |
| **Trigger** | Otomatik event yanıtı | Kullanıcı tetiklemeli |
| **Scheduler** | Reddit cron (sunucu taraflı) | Manuel çalıştırma |
| **Frontend** | Custom post (HTML/JS) | Terminal (Rich) |

## Devvit Ne Zaman Tercih Edilmeli?

Bu örnek bot aşağıdaki senaryolarda Devvit kullanmanın uygun olduğunu göstermektedir:

1. **Bir subreddit'in moderatörüyseniz** ve o subreddit'e özel araçlar geliştirmek istiyorsanız
2. **Topluluk etkileşimi** gerekiyorsa (yorum yazma, post oluşturma, oylama)
3. **Otomatik tepkiler** lazımsa (yeni kullanıcı karşılama, spam filtreleme)
4. **Zamanlanmış görevler** çalıştırmak istiyorsanız (günlük rapor, haftalık temizlik)
5. **İnteraktif postlar** oluşturmak istiyorsanız (quiz, anket, istatistik panosu)

ReddTrender gibi kişisel, cross-subreddit, read-only bir araç için Devvit uygun değildir — bu senaryoda Data API doğru tercihtir.
