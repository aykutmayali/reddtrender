"""
RedditTrender - Reddit API istemcisi
OAuth2 Script App kimlik doğrulaması ile Reddit API'ye bağlanır.
Rate limit takibi ve otomatik bekleme mekanizması içerir.
"""

import time
import requests
import config


class RedditClient:
    """Reddit OAuth2 API istemcisi."""

    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self.session = requests.Session()
        self._authenticate()

    def _authenticate(self):
        """
        Script App tipi için OAuth2 password grant akışı ile kimlik doğrulaması.
        Reddit Responsible Builder Policy gereği user-agent zorunludur.
        """
        if not config.CLIENT_ID or config.CLIENT_ID == "your_client_id_here":
            raise ValueError(
                "Reddit API kimlik bilgileri yapılandırılmamış!\n"
                "Lütfen .env dosyasını oluşturun ve bilgilerinizi girin.\n"
                "Detaylar için README.md dosyasına bakın."
            )

        auth = requests.auth.HTTPBasicAuth(config.CLIENT_ID, config.CLIENT_SECRET)
        headers = {"User-Agent": config.USER_AGENT}

        response = requests.post(
            config.AUTH_URL,
            auth=auth,
            data={
                "grant_type": "password",
                "username": config.USERNAME,
                "password": config.PASSWORD,
            },
            headers=headers,
        )

        if response.status_code != 200:
            raise ConnectionError(
                f"Reddit API kimlik doğrulaması başarısız! "
                f"HTTP {response.status_code}: {response.text}"
            )

        token_data = response.json()

        if "error" in token_data:
            raise ConnectionError(
                f"Kimlik doğrulama hatası: {token_data['error']}"
            )

        self.access_token = token_data["access_token"]
        self.token_expires_at = time.time() + token_data["expires_in"]
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": config.USER_AGENT,
            }
        )

    def _ensure_token(self):
        """Token süresi dolmuşsa yenile."""
        if time.time() >= self.token_expires_at - 60:
            self._authenticate()

    def _check_rate_limit(self, response):
        """
        Reddit rate limit başlıklarını kontrol et.
        Ücretsiz katman: dakika başına 100 istek.
        """
        remaining = response.headers.get("X-Ratelimit-Remaining")
        reset = response.headers.get("X-Ratelimit-Reset")

        if remaining is not None and reset is not None:
            remaining = float(remaining)
            reset = float(reset)

            if remaining < config.RATE_LIMIT_BUFFER:
                wait_time = reset + 1
                print(
                    f"  ⏳ Rate limit yaklaşıyor ({int(remaining)} istek kaldı). "
                    f"{int(wait_time)} saniye bekleniyor..."
                )
                time.sleep(wait_time)

    def _get(self, endpoint, params=None):
        """
        Rate limit kontrolü ile GET isteği gönder.
        429 hatasında exponential backoff uygular.
        """
        self._ensure_token()

        if params is None:
            params = {}

        url = f"{config.BASE_URL}{endpoint}"

        for attempt in range(3):
            response = self.session.get(url, params=params)

            if response.status_code == 429:
                wait = (2 ** attempt) * 5
                print(f"  ⏳ 429 Too Many Requests. {wait} saniye bekleniyor...")
                time.sleep(wait)
                continue

            if response.status_code == 401:
                self._authenticate()
                response = self.session.get(url, params=params)

            self._check_rate_limit(response)
            return response

        raise ConnectionError("Maksimum yeniden deneme sayısına ulaşıldı (429).")

    def get_hot(self, subreddit="popular", limit=None):
        """Bir subreddit'in popüler (hot) gönderilerini getir."""
        limit = limit or config.DEFAULT_LIMIT
        response = self._get(f"/r/{subreddit}/hot", {"limit": limit})
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def get_rising(self, subreddit="popular", limit=None):
        """Yükselişte olan (rising) gönderileri getir."""
        limit = limit or config.DEFAULT_LIMIT
        response = self._get(f"/r/{subreddit}/rising", {"limit": limit})
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def get_top(self, subreddit="popular", time_filter="day", limit=None):
        """Belirli zaman aralığında en çok oy alan gönderileri getir."""
        limit = limit or config.DEFAULT_LIMIT
        response = self._get(
            f"/r/{subreddit}/top",
            {"t": time_filter, "limit": limit},
        )
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def get_popular(self, limit=None):
        """Reddit genelindeki popüler gönderileri getir."""
        limit = limit or config.DEFAULT_LIMIT
        response = self._get("/r/popular", {"limit": limit})
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def get_best(self, limit=None):
        """Kimliği doğrulanmış kullanıcı için en iyi gönderileri getir."""
        limit = limit or config.DEFAULT_LIMIT
        response = self._get("/best", {"limit": limit})
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def get_subreddit_posts(self, subreddit, sort="hot", limit=None, time_filter="day"):
        """Belirtilen subredditten gönderileri getir."""
        limit = limit or config.DEFAULT_LIMIT
        params = {"limit": limit}
        if sort == "top":
            params["t"] = time_filter
        response = self._get(f"/r/{subreddit}/{sort}", params)
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    def search(self, query, subreddit=None, sort="relevance", time_filter="all", limit=None):
        """Reddit'te arama yap."""
        limit = limit or config.DEFAULT_LIMIT
        params = {
            "q": query,
            "sort": sort,
            "t": time_filter,
            "limit": limit,
        }
        if subreddit:
            params["restrict_sr"] = "on"
            endpoint = f"/r/{subreddit}/search"
        else:
            endpoint = "/search"

        response = self._get(endpoint, params)
        if response.status_code == 200:
            return self._parse_posts(response.json())
        return []

    @staticmethod
    def _parse_posts(data):
        """API yanıtından gönderi verilerini ayrıştır."""
        posts = []
        children = data.get("data", {}).get("children", [])

        for child in children:
            post_data = child.get("data", {})
            posts.append({
                "id": post_data.get("id", ""),
                "title": post_data.get("title", ""),
                "subreddit": post_data.get("subreddit_name_prefixed", ""),
                "author": post_data.get("author", "[deleted]"),
                "score": post_data.get("score", 0),
                "upvote_ratio": post_data.get("upvote_ratio", 0),
                "num_comments": post_data.get("num_comments", 0),
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "created_utc": post_data.get("created_utc", 0),
                "selftext": (post_data.get("selftext", "") or "")[:200],
                "is_self": post_data.get("is_self", True),
                "link_flair_text": post_data.get("link_flair_text", ""),
                "over_18": post_data.get("over_18", False),
                "spoiler": post_data.get("spoiler", False),
                "stickied": post_data.get("stickied", False),
            })

        return posts
