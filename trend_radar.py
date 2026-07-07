"""
Trend Radar service for collecting, comparing, and exporting Reddit snapshots.
"""

import csv
import os
from datetime import datetime, timezone

import config
from storage import TrendStore


class TrendRadarService:
    """Coordinates Reddit collection, local snapshots, and trend reporting."""

    def __init__(self, client=None, store=None):
        self.client = client
        self.store = store or TrendStore()

    def collect_snapshot(self, subreddits=None, limit=None, keywords=None, label=None):
        """Collect a fresh Reddit snapshot and persist it locally."""
        if self.client is None:
            raise ValueError("Snapshot almak için RedditClient gerekiyor.")

        limit = limit or config.DEFAULT_LIMIT
        keywords = keywords if keywords is not None else config.DEFAULT_KEYWORDS
        selected_subreddits = self._normalize_subreddits(subreddits or config.DEFAULT_SUBREDDITS)

        posts = []
        posts.extend(self._with_category(self.client.get_popular(limit=limit), "Popular"))
        posts.extend(self._with_category(self.client.get_rising("popular", limit=limit), "Rising"))
        posts.extend(
            self._with_category(
                self.client.get_top("popular", time_filter="day", limit=limit),
                "Top Today",
            )
        )

        per_subreddit_limit = max(5, min(limit, 15))
        for subreddit in selected_subreddits:
            fetched = self.client.get_subreddit_posts(
                subreddit,
                sort="hot",
                limit=per_subreddit_limit,
            )
            posts.extend(self._with_category(fetched, f"r/{subreddit} Hot"))

        snapshot_id = self.store.create_snapshot(
            posts,
            label=label,
            source="reddit-api",
            notes=f"limit={limit}; subreddits={','.join(selected_subreddits)}",
            keywords=keywords,
        )

        snapshot = self.store.get_snapshot(snapshot_id)
        return {
            "snapshot": snapshot,
            "posts": self.store.get_posts(snapshot_id),
            "subreddit_metrics": self.store.get_subreddit_metrics(snapshot_id),
            "alerts": self.store.get_keyword_alerts(snapshot_id),
        }

    def build_radar(self, snapshot_id=None, top_n=15):
        """Build a trend radar report from the latest or selected snapshot."""
        current = self.store.get_snapshot(snapshot_id)
        if not current:
            raise ValueError("Henüz kayıtlı snapshot yok. Önce --snapshot çalıştırın.")

        previous = self.store.get_previous_snapshot(current["id"])
        current_posts = self.store.get_posts(current["id"])
        previous_posts = self.store.get_posts(previous["id"]) if previous else []
        current_metrics = self.store.get_subreddit_metrics(current["id"])
        previous_metrics = self.store.get_subreddit_metrics(previous["id"]) if previous else []

        ranked_posts = self._rank_posts(current, current_posts, previous, previous_posts)
        subreddit_deltas = self._compare_subreddits(current_metrics, previous_metrics)

        return {
            "snapshot": current,
            "previous_snapshot": previous,
            "top_posts": ranked_posts[:top_n],
            "subreddit_deltas": subreddit_deltas,
            "alerts": self.store.get_keyword_alerts(current["id"]),
        }

    def export_markdown(self, report, output_path=None):
        """Write a Markdown report and return the output path."""
        output_path = output_path or self._default_output_path("md")
        self._ensure_parent_dir(output_path)

        snapshot = report["snapshot"]
        previous = report.get("previous_snapshot")
        lines = [
            "# ReddTrender Trend Radar",
            "",
            f"- Snapshot: #{snapshot['id']} ({snapshot['created_at']})",
            f"- Gonderi sayisi: {snapshot['post_count']}",
            f"- Onceki snapshot: #{previous['id']} ({previous['created_at']})" if previous else "- Onceki snapshot: yok",
            "",
            "## En Hizli Yukselenler",
            "",
            "| # | Subreddit | Momentum | Skor Farki | Yorum Farki | Baslik |",
            "|---|-----------|----------|------------|-------------|--------|",
        ]

        for index, post in enumerate(report["top_posts"], 1):
            lines.append(
                "| {index} | {subreddit} | {momentum} | {score_delta:+d} | "
                "{comment_delta:+d} | [{title}]({url}) |".format(
                    index=index,
                    subreddit=self._escape_md(post["subreddit"]),
                    momentum=post["momentum_score"],
                    score_delta=post["score_delta"],
                    comment_delta=post["comment_delta"],
                    title=self._escape_md(post["title"]),
                    url=post["url"],
                )
            )

        lines.extend(
            [
                "",
                "## Subreddit Isisi",
                "",
                "| Subreddit | Isi | Fark | Gonderi | En iyi gonderi |",
                "|-----------|-----|------|---------|----------------|",
            ]
        )
        for metric in report["subreddit_deltas"][:15]:
            lines.append(
                "| {subreddit} | {heat} | {heat_delta:+d} | {post_count} | [{title}]({url}) |".format(
                    subreddit=self._escape_md(metric["subreddit"]),
                    heat=metric["heat_index"],
                    heat_delta=metric["heat_delta"],
                    post_count=metric["post_count"],
                    title=self._escape_md(metric["top_post_title"]),
                    url=metric["top_post_url"],
                )
            )

        lines.extend(["", "## Keyword Alarmlari", ""])
        if report["alerts"]:
            lines.extend(
                [
                    "| Keyword | Subreddit | Skor | Baslik |",
                    "|---------|-----------|------|--------|",
                ]
            )
            for alert in report["alerts"][:30]:
                lines.append(
                    "| {keyword} | {subreddit} | {score} | [{title}]({url}) |".format(
                        keyword=self._escape_md(alert["keyword"]),
                        subreddit=self._escape_md(alert["subreddit"]),
                        score=alert["score"],
                        title=self._escape_md(alert["title"]),
                        url=alert["url"],
                    )
                )
        else:
            lines.append("Bu snapshot icin keyword alarmi yok.")

        with open(output_path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

        return output_path

    def export_csv(self, report, output_path=None):
        """Write top momentum posts as CSV and return the output path."""
        output_path = output_path or self._default_output_path("csv")
        self._ensure_parent_dir(output_path)

        fieldnames = [
            "rank",
            "snapshot_id",
            "subreddit",
            "title",
            "url",
            "score",
            "score_delta",
            "num_comments",
            "comment_delta",
            "momentum_score",
            "trend_category",
        ]
        with open(output_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for index, post in enumerate(report["top_posts"], 1):
                writer.writerow(
                    {
                        "rank": index,
                        "snapshot_id": report["snapshot"]["id"],
                        "subreddit": post["subreddit"],
                        "title": post["title"],
                        "url": post["url"],
                        "score": post["score"],
                        "score_delta": post["score_delta"],
                        "num_comments": post["num_comments"],
                        "comment_delta": post["comment_delta"],
                        "momentum_score": post["momentum_score"],
                        "trend_category": post.get("trend_category", ""),
                    }
                )

        return output_path

    @staticmethod
    def _with_category(posts, category):
        enriched = []
        for post in posts:
            copied = dict(post)
            copied["trend_category"] = category
            enriched.append(copied)
        return enriched

    @staticmethod
    def _normalize_subreddits(subreddits):
        if isinstance(subreddits, str):
            subreddits = subreddits.split(",")

        normalized = []
        for subreddit in subreddits:
            subreddit = subreddit.strip()
            if subreddit.startswith("r/"):
                subreddit = subreddit[2:]
            if subreddit:
                normalized.append(subreddit)
        return normalized

    def _rank_posts(self, current_snapshot, current_posts, previous_snapshot, previous_posts):
        previous_by_id = {post["id"]: post for post in previous_posts}
        current_time = self._parse_snapshot_time(current_snapshot["created_at"])
        previous_time = (
            self._parse_snapshot_time(previous_snapshot["created_at"])
            if previous_snapshot
            else None
        )
        snapshot_hours = self._hours_between(previous_time, current_time) if previous_time else None

        ranked = []
        for post in current_posts:
            previous = previous_by_id.get(post["id"])
            if previous:
                score_delta = int(post["score"]) - int(previous["score"])
                comment_delta = int(post["num_comments"]) - int(previous["num_comments"])
                elapsed_hours = max(snapshot_hours or 1, 0.25)
                is_new = False
            else:
                score_delta = int(post["score"])
                comment_delta = int(post["num_comments"])
                elapsed_hours = self._post_age_hours(post, current_time)
                is_new = True

            ratio = max(float(post.get("upvote_ratio") or 0), 0.1)
            positive_activity = max(score_delta, 0) + max(comment_delta, 0) * 2
            if is_new:
                positive_activity += int(post["score"]) * 0.1 + int(post["num_comments"]) * 0.25

            momentum_score = round((positive_activity / max(elapsed_hours, 0.25)) * ratio, 2)
            ranked.append(
                {
                    **post,
                    "previous_score": int(previous["score"]) if previous else 0,
                    "previous_comments": int(previous["num_comments"]) if previous else 0,
                    "score_delta": score_delta,
                    "comment_delta": comment_delta,
                    "momentum_score": momentum_score,
                    "is_new": is_new,
                }
            )

        ranked.sort(
            key=lambda post: (
                post["momentum_score"],
                post["score_delta"],
                post["comment_delta"],
                post["score"],
            ),
            reverse=True,
        )
        return ranked

    @staticmethod
    def _compare_subreddits(current_metrics, previous_metrics):
        previous_by_subreddit = {
            metric["subreddit"]: metric for metric in previous_metrics
        }
        compared = []

        for metric in current_metrics:
            previous = previous_by_subreddit.get(metric["subreddit"])
            heat_delta = metric["heat_index"] - previous["heat_index"] if previous else metric["heat_index"]
            score_delta = metric["total_score"] - previous["total_score"] if previous else metric["total_score"]
            comment_delta = metric["total_comments"] - previous["total_comments"] if previous else metric["total_comments"]
            compared.append(
                {
                    **metric,
                    "heat_delta": heat_delta,
                    "score_delta": score_delta,
                    "comment_delta": comment_delta,
                    "is_new": previous is None,
                }
            )

        compared.sort(key=lambda item: (item["heat_delta"], item["heat_index"]), reverse=True)
        return compared

    @staticmethod
    def _parse_snapshot_time(value):
        return datetime.fromisoformat(value)

    @staticmethod
    def _hours_between(start, end):
        return max((end - start).total_seconds() / 3600, 0.25)

    @staticmethod
    def _post_age_hours(post, current_time):
        created_utc = post.get("created_utc")
        if not created_utc:
            return 24
        created = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
        return max((current_time - created).total_seconds() / 3600, 0.25)

    @staticmethod
    def _ensure_parent_dir(path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @staticmethod
    def _default_output_path(extension):
        os.makedirs(config.REPORT_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return os.path.join(config.REPORT_DIR, f"trend-radar-{stamp}.{extension}")

    @staticmethod
    def _escape_md(value):
        return str(value or "").replace("|", "\\|").replace("\n", " ")
