"""
RedditTrender - Trend analiz modülü
Reddit verilerinden trend bilgilerini çıkarır ve analiz eder.
"""

from collections import Counter
from datetime import datetime, timezone


class TrendAnalyzer:
    """Reddit gönderilerinden trend analizi yapan sınıf."""

    def __init__(self, client):
        self.client = client

    def get_trending_subreddits(self, subreddits=None, sort="hot", limit=10):
        """
        Belirtilen subredditler arasında trend analizi yapar.
        Her subredditten en popüler gönderileri toplar ve
        toplam skor/yorum sayısına göre sıralar.
        """
        if subreddits is None:
            import config
            subreddits = config.DEFAULT_SUBREDDITS

        trends = []

        for sub in subreddits:
            try:
                posts = self.client.get_subreddit_posts(sub, sort=sort, limit=limit)
                if not posts:
                    continue

                total_score = sum(p["score"] for p in posts)
                total_comments = sum(p["num_comments"] for p in posts)
                avg_score = total_score / len(posts) if posts else 0
                top_post = max(posts, key=lambda p: p["score"]) if posts else None

                trends.append({
                    "subreddit": f"r/{sub}",
                    "total_score": total_score,
                    "total_comments": total_comments,
                    "avg_score": int(avg_score),
                    "post_count": len(posts),
                    "top_post_title": top_post["title"] if top_post else "",
                    "top_post_score": top_post["score"] if top_post else 0,
                    "top_post_url": top_post["url"] if top_post else "",
                    "heat_index": self._calculate_heat(total_score, total_comments, len(posts)),
                })
            except Exception as e:
                print(f"  ⚠️  r/{sub} verileri alınamadı: {e}")
                continue

        # Isı endeksine göre sırala
        trends.sort(key=lambda t: t["heat_index"], reverse=True)
        return trends

    def get_rising_trends(self, limit=25):
        """
        Yükselişte olan (rising) gönderileri analiz eder.
        Score/comment oranına göre viral potansiyeli hesaplar.
        """
        rising = self.client.get_rising("popular", limit=limit)

        analyzed = []
        for post in rising:
            viral_score = self._calculate_viral_score(post)
            analyzed.append({
                **post,
                "viral_score": viral_score,
                "engagement_rate": self._engagement_rate(post),
            })

        analyzed.sort(key=lambda p: p["viral_score"], reverse=True)
        return analyzed

    def get_hot_topics(self, limit=50):
        """
        Popüler gönderilerden sıcak konuları çıkarır.
        Gönderi başlıklarındaki kelimeleri analiz eder.
        """
        posts = self.client.get_popular(limit=limit)
        if not posts:
            return {"posts": [], "top_words": [], "subreddits": []}

        # Kelime frekans analizi
        all_words = []
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "or", "but", "not", "no", "so", "if", "it", "its",
            "this", "that", "these", "those", "i", "you", "he", "she",
            "we", "they", "me", "him", "her", "us", "them", "my", "your",
            "his", "our", "their", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "than", "too", "very", "just",
            "about", "up", "out", "as", "into", "after", "before", "new",
        }

        for post in posts:
            title = post["title"].lower()
            words = [w.strip(".,!?;:'\"()-[]{}") for w in title.split()]
            all_words.extend(w for w in words if len(w) > 2 and w not in stop_words)

        word_freq = Counter(all_words).most_common(15)

        # Subreddit dağılımı
        sub_counter = Counter(p["subreddit"] for p in posts)
        top_subs = sub_counter.most_common(10)

        return {
            "posts": posts[:25],
            "top_words": word_freq,
            "top_subreddits": top_subs,
        }

    def get_daily_summary(self):
        """
        Günlük trend özeti oluşturur.
        Popüler, yükselişte olan ve en çok oy alan gönderileri birleştirir.
        """
        popular = self.client.get_popular(limit=15)
        rising = self.client.get_rising("popular", limit=10)
        top_today = self.client.get_top("popular", time_filter="day", limit=10)

        # Benzersiz gönderileri birleştir
        seen_ids = set()
        all_trending = []

        for post_list, category in [
            (popular, "Popular"),
            (rising, "Rising"),
            (top_today, "Top Today"),
        ]:
            for post in post_list:
                if post["id"] not in seen_ids:
                    seen_ids.add(post["id"])
                    post["trend_category"] = category
                    all_trending.append(post)

        # Skora göre sırala
        all_trending.sort(key=lambda p: p["score"], reverse=True)

        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "total_posts": len(all_trending),
            "popular_count": len(popular),
            "rising_count": len(rising),
            "top_count": len(top_today),
            "posts": all_trending,
        }

    @staticmethod
    def _calculate_heat(total_score, total_comments, post_count):
        """
        Isı endeksi hesaplar.
        Skor, yorum sayısı ve gönderi sayısının ağırlıklı ortalaması.
        """
        if post_count == 0:
            return 0
        score_component = total_score * 0.5
        comment_component = total_comments * 0.3
        volume_component = post_count * 100 * 0.2
        return int(score_component + comment_component + volume_component)

    @staticmethod
    def _calculate_viral_score(post):
        """
        Viral potansiyel skoru hesaplar.
        Skor/yorum oranı ve upvote_ratio'yu dikkate alır.
        """
        score = post.get("score", 0)
        comments = post.get("num_comments", 0)
        ratio = post.get("upvote_ratio", 0)

        engagement = score + comments * 2
        return int(engagement * ratio)

    @staticmethod
    def _engagement_rate(post):
        """Etkileşim oranı hesaplar (yorum/skor)."""
        score = post.get("score", 1)
        comments = post.get("num_comments", 0)
        if score == 0:
            return 0
        return round((comments / score) * 100, 2)
