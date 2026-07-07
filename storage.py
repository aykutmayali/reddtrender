"""
SQLite persistence for ReddTrender snapshots.

The store keeps historical post snapshots local to the machine so trend deltas
can be calculated without depending on an external database.
"""

import os
import sqlite3
from datetime import datetime, timezone

import config


class TrendStore:
    """Small SQLite repository for trend snapshots and derived alerts."""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        self._ensure_parent_dir()
        self._initialize()

    def _ensure_parent_dir(self):
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    label TEXT,
                    source TEXT NOT NULL,
                    post_count INTEGER NOT NULL DEFAULT 0,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS posts (
                    snapshot_id INTEGER NOT NULL,
                    post_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    author TEXT,
                    score INTEGER NOT NULL DEFAULT 0,
                    upvote_ratio REAL NOT NULL DEFAULT 0,
                    num_comments INTEGER NOT NULL DEFAULT 0,
                    url TEXT,
                    created_utc REAL,
                    selftext TEXT,
                    is_self INTEGER NOT NULL DEFAULT 0,
                    link_flair_text TEXT,
                    over_18 INTEGER NOT NULL DEFAULT 0,
                    spoiler INTEGER NOT NULL DEFAULT 0,
                    stickied INTEGER NOT NULL DEFAULT 0,
                    trend_category TEXT,
                    PRIMARY KEY (snapshot_id, post_id),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS subreddit_metrics (
                    snapshot_id INTEGER NOT NULL,
                    subreddit TEXT NOT NULL,
                    post_count INTEGER NOT NULL DEFAULT 0,
                    total_score INTEGER NOT NULL DEFAULT 0,
                    total_comments INTEGER NOT NULL DEFAULT 0,
                    avg_score INTEGER NOT NULL DEFAULT 0,
                    max_score INTEGER NOT NULL DEFAULT 0,
                    heat_index INTEGER NOT NULL DEFAULT 0,
                    top_post_id TEXT,
                    top_post_title TEXT,
                    top_post_url TEXT,
                    PRIMARY KEY (snapshot_id, subreddit),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS keyword_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    subreddit TEXT NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    num_comments INTEGER NOT NULL DEFAULT 0,
                    url TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_created_at
                    ON snapshots(created_at);
                CREATE INDEX IF NOT EXISTS idx_posts_post_id
                    ON posts(post_id);
                CREATE INDEX IF NOT EXISTS idx_posts_subreddit
                    ON posts(snapshot_id, subreddit);
                CREATE INDEX IF NOT EXISTS idx_alerts_snapshot_keyword
                    ON keyword_alerts(snapshot_id, keyword);
                """
            )

    def create_snapshot(
        self,
        posts,
        label=None,
        source="trend-radar",
        notes=None,
        keywords=None,
        subreddit_metrics=None,
    ):
        """Persist one snapshot and return its id."""
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        unique_posts = self._dedupe_posts(posts)
        metrics = subreddit_metrics or self.build_subreddit_metrics(unique_posts)
        alert_rows = self._build_keyword_alerts(unique_posts, keywords or [], created_at)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshots (created_at, label, source, post_count, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (created_at, label, source, len(unique_posts), notes),
            )
            snapshot_id = cursor.lastrowid

            conn.executemany(
                """
                INSERT INTO posts (
                    snapshot_id, post_id, title, subreddit, author, score,
                    upvote_ratio, num_comments, url, created_utc, selftext,
                    is_self, link_flair_text, over_18, spoiler, stickied,
                    trend_category
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [self._post_row(snapshot_id, post) for post in unique_posts],
            )

            conn.executemany(
                """
                INSERT INTO subreddit_metrics (
                    snapshot_id, subreddit, post_count, total_score,
                    total_comments, avg_score, max_score, heat_index,
                    top_post_id, top_post_title, top_post_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._metric_row(snapshot_id, metric) for metric in metrics],
            )

            conn.executemany(
                """
                INSERT INTO keyword_alerts (
                    snapshot_id, keyword, post_id, title, subreddit, score,
                    num_comments, url, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        alert["keyword"],
                        alert["post_id"],
                        alert["title"],
                        alert["subreddit"],
                        alert["score"],
                        alert["num_comments"],
                        alert["url"],
                        alert["created_at"],
                    )
                    for alert in alert_rows
                ],
            )

        return snapshot_id

    def list_snapshots(self, limit=10):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, label, source, post_count, notes
                FROM snapshots
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_snapshot(self, snapshot_id=None):
        with self._connect() as conn:
            if snapshot_id is None:
                row = conn.execute(
                    """
                    SELECT id, created_at, label, source, post_count, notes
                    FROM snapshots
                    ORDER BY datetime(created_at) DESC, id DESC
                    LIMIT 1
                    """
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, created_at, label, source, post_count, notes
                    FROM snapshots
                    WHERE id = ?
                    """,
                    (snapshot_id,),
                ).fetchone()
        return dict(row) if row else None

    def get_previous_snapshot(self, snapshot_id):
        current = self.get_snapshot(snapshot_id)
        if not current:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, created_at, label, source, post_count, notes
                FROM snapshots
                WHERE datetime(created_at) < datetime(?)
                   OR (created_at = ? AND id < ?)
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """,
                (current["created_at"], current["created_at"], snapshot_id),
            ).fetchone()
        return dict(row) if row else None

    def get_posts(self, snapshot_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT post_id AS id, title, subreddit, author, score,
                       upvote_ratio, num_comments, url, created_utc,
                       selftext, is_self, link_flair_text, over_18,
                       spoiler, stickied, trend_category
                FROM posts
                WHERE snapshot_id = ?
                ORDER BY score DESC, num_comments DESC
                """,
                (snapshot_id,),
            ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def get_subreddit_metrics(self, snapshot_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT subreddit, post_count, total_score, total_comments,
                       avg_score, max_score, heat_index, top_post_id,
                       top_post_title, top_post_url
                FROM subreddit_metrics
                WHERE snapshot_id = ?
                ORDER BY heat_index DESC
                """,
                (snapshot_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_keyword_alerts(self, snapshot_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT keyword, post_id, title, subreddit, score,
                       num_comments, url, created_at
                FROM keyword_alerts
                WHERE snapshot_id = ?
                ORDER BY score DESC, num_comments DESC
                """,
                (snapshot_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def build_subreddit_metrics(posts):
        grouped = {}
        for post in posts:
            subreddit = post.get("subreddit") or "unknown"
            bucket = grouped.setdefault(subreddit, [])
            bucket.append(post)

        metrics = []
        for subreddit, sub_posts in grouped.items():
            total_score = sum(int(post.get("score") or 0) for post in sub_posts)
            total_comments = sum(int(post.get("num_comments") or 0) for post in sub_posts)
            top_post = max(sub_posts, key=lambda post: int(post.get("score") or 0))
            post_count = len(sub_posts)
            avg_score = int(total_score / post_count) if post_count else 0
            heat_index = int(total_score * 0.5 + total_comments * 0.3 + post_count * 20)
            metrics.append(
                {
                    "subreddit": subreddit,
                    "post_count": post_count,
                    "total_score": total_score,
                    "total_comments": total_comments,
                    "avg_score": avg_score,
                    "max_score": int(top_post.get("score") or 0),
                    "heat_index": heat_index,
                    "top_post_id": top_post.get("id", ""),
                    "top_post_title": top_post.get("title", ""),
                    "top_post_url": top_post.get("url", ""),
                }
            )

        metrics.sort(key=lambda item: item["heat_index"], reverse=True)
        return metrics

    @staticmethod
    def _dedupe_posts(posts):
        by_id = {}
        category_sets = {}
        for post in posts:
            post_id = post.get("id")
            if not post_id:
                continue
            if post_id not in by_id:
                by_id[post_id] = dict(post)
                category_sets[post_id] = set()
            category = post.get("trend_category")
            if category:
                category_sets[post_id].add(str(category))

            existing = by_id[post_id]
            if int(post.get("score") or 0) > int(existing.get("score") or 0):
                by_id[post_id].update(post)

        for post_id, categories in category_sets.items():
            if categories:
                by_id[post_id]["trend_category"] = ", ".join(sorted(categories))

        return list(by_id.values())

    @staticmethod
    def _build_keyword_alerts(posts, keywords, created_at):
        normalized = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
        alerts = []

        for post in posts:
            text = f"{post.get('title', '')} {post.get('selftext', '')}".lower()
            for keyword in normalized:
                if keyword in text:
                    alerts.append(
                        {
                            "keyword": keyword,
                            "post_id": post.get("id", ""),
                            "title": post.get("title", ""),
                            "subreddit": post.get("subreddit", ""),
                            "score": int(post.get("score") or 0),
                            "num_comments": int(post.get("num_comments") or 0),
                            "url": post.get("url", ""),
                            "created_at": created_at,
                        }
                    )

        return alerts

    @staticmethod
    def _post_row(snapshot_id, post):
        return (
            snapshot_id,
            post.get("id", ""),
            post.get("title", ""),
            post.get("subreddit", ""),
            post.get("author", ""),
            int(post.get("score") or 0),
            float(post.get("upvote_ratio") or 0),
            int(post.get("num_comments") or 0),
            post.get("url", ""),
            float(post.get("created_utc") or 0),
            post.get("selftext", ""),
            1 if post.get("is_self") else 0,
            post.get("link_flair_text", ""),
            1 if post.get("over_18") else 0,
            1 if post.get("spoiler") else 0,
            1 if post.get("stickied") else 0,
            post.get("trend_category", ""),
        )

    @staticmethod
    def _metric_row(snapshot_id, metric):
        return (
            snapshot_id,
            metric["subreddit"],
            metric["post_count"],
            metric["total_score"],
            metric["total_comments"],
            metric["avg_score"],
            metric["max_score"],
            metric["heat_index"],
            metric.get("top_post_id", ""),
            metric.get("top_post_title", ""),
            metric.get("top_post_url", ""),
        )

    @staticmethod
    def _row_to_post(row):
        post = dict(row)
        post["is_self"] = bool(post["is_self"])
        post["over_18"] = bool(post["over_18"])
        post["spoiler"] = bool(post["spoiler"])
        post["stickied"] = bool(post["stickied"])
        return post
