"""
Opportunity Radar for turning Reddit trend snapshots into app ideas.

The service is intentionally deterministic: it scores existing snapshot posts
against a curated set of Reddit/Devvit product opportunity categories without
calling external AI services or sending Reddit data anywhere.
"""

import os
import re
from datetime import datetime, timezone

import config
from storage import TrendStore
from trend_radar import TrendRadarService


OPPORTUNITY_CATEGORIES = {
    "ai-content-moderation": {
        "name": "AI Content Moderation",
        "platform_fit": "Devvit mod tool",
        "target_user": "Subreddit moderators",
        "monetization": "Developer Funds, paid premium rules, moderator SaaS",
        "mvp": "Score new posts/comments for AI-like, spammy, or low-effort patterns and explain the reason to mods.",
        "keywords": [
            "ai",
            "ai-generated",
            "chatgpt",
            "openai",
            "llm",
            "bot",
            "spam",
            "slop",
            "low effort",
            "moderation",
            "modqueue",
            "automod",
            "repost",
            "fake",
        ],
    },
    "mod-queue-ops": {
        "name": "Mod Queue Operations",
        "platform_fit": "Devvit mod tool",
        "target_user": "Moderation teams",
        "monetization": "Developer Funds, install-based reach, team workflow upgrades",
        "mvp": "Prioritize queue items, show moderator presence, preserve action history, and suggest removal reasons.",
        "keywords": [
            "modqueue",
            "moderator",
            "moderation",
            "report",
            "ban",
            "appeal",
            "harassment",
            "brigading",
            "raid",
            "evasion",
            "spam",
            "rule",
            "queue",
            "automod",
        ],
    },
    "subreddit-analytics": {
        "name": "Subreddit Analytics",
        "platform_fit": "Hybrid: Data API research plus Devvit community dashboard",
        "target_user": "Mods, creators, community managers",
        "monetization": "Low-cost subscription, weekly reports, Developer Funds for Devvit version",
        "mvp": "Track heat, momentum, active topics, best posting windows, and weekly community health notes.",
        "keywords": [
            "analytics",
            "metrics",
            "dashboard",
            "growth",
            "trend",
            "trending",
            "engagement",
            "traffic",
            "community",
            "subreddit",
            "report",
            "insight",
            "performance",
        ],
    },
    "daily-community-games": {
        "name": "Daily Community Games",
        "platform_fit": "Devvit interactive experience",
        "target_user": "Reddit communities and players",
        "monetization": "Developer Funds, in-app purchases, sponsored community events",
        "mvp": "Daily quiz, prediction, or puzzle loop with streaks, leaderboards, flair rewards, and shareable results.",
        "keywords": [
            "game",
            "games",
            "trivia",
            "quiz",
            "puzzle",
            "daily",
            "streak",
            "leaderboard",
            "challenge",
            "prediction",
            "score",
            "sports",
            "fantasy",
        ],
    },
    "accessibility-and-summary": {
        "name": "Accessibility and Summaries",
        "platform_fit": "Devvit utility with approved AI fetch where needed",
        "target_user": "Readers, mods, multilingual communities",
        "monetization": "Developer Funds, premium community packs",
        "mvp": "Generate TL;DR summaries, alt text reminders, translation helpers, and long-thread digest cards.",
        "keywords": [
            "accessibility",
            "alt text",
            "translate",
            "translation",
            "tldr",
            "summary",
            "summarize",
            "long post",
            "image description",
            "language",
            "caption",
        ],
    },
    "settings-backup": {
        "name": "Subreddit Backup and Recovery",
        "platform_fit": "Devvit mod tool",
        "target_user": "Subreddit owners and senior mods",
        "monetization": "Developer Funds, premium retention and diff history",
        "mvp": "Snapshot AutoMod, wiki, flair, rules, and settings with diff views and one-click restore guidance.",
        "keywords": [
            "automod",
            "wiki",
            "rules",
            "flair",
            "settings",
            "backup",
            "restore",
            "config",
            "configuration",
            "css",
            "mod tools",
        ],
    },
    "market-research-local": {
        "name": "Reddit Market Research",
        "platform_fit": "Data API dashboard",
        "target_user": "Indie hackers, SaaS builders, product teams",
        "monetization": "Subscription, saved research workspaces, private reports",
        "mvp": "Detect repeated pain points, buyer intent, competitor mentions, and idea clusters from public threads.",
        "keywords": [
            "startup",
            "saas",
            "app idea",
            "product",
            "pricing",
            "competitor",
            "alternative",
            "would pay",
            "need an app",
            "looking for tool",
            "pain point",
            "workflow",
        ],
    },
}


class OpportunityRadarService:
    """Ranks app opportunities from locally stored trend snapshots."""

    def __init__(self, store=None, categories=None):
        self.store = store or TrendStore()
        self.categories = categories or OPPORTUNITY_CATEGORIES

    def build(self, snapshot_id=None, top_n=10, category_key=None):
        """Build an opportunity report for the latest or selected snapshot."""
        current = self.store.get_snapshot(snapshot_id)
        if not current:
            raise ValueError("Opportunity Radar icin snapshot yok. Once --snapshot calistirin.")

        posts = self.store.get_posts(current["id"])
        if not posts:
            return {
                "snapshot": current,
                "previous_snapshot": self.store.get_previous_snapshot(current["id"]),
                "opportunities": [],
            }

        radar = TrendRadarService(store=self.store).build_radar(
            current["id"],
            top_n=max(len(posts), 1),
        )
        ranked_posts = radar["top_posts"]
        selected_categories = self._select_categories(category_key)

        opportunities = []
        for key, category in selected_categories.items():
            evidence = self._evidence_for_category(category, ranked_posts)
            if not evidence:
                continue

            matched_keywords = sorted(
                {keyword for item in evidence for keyword in item["matched_keywords"]}
            )
            unique_subreddits = sorted({item["subreddit"] for item in evidence})
            score = self._score_category(evidence, matched_keywords, unique_subreddits)
            opportunities.append(
                {
                    "key": key,
                    "name": category["name"],
                    "score": score,
                    "confidence": self._confidence(score, evidence, unique_subreddits),
                    "platform_fit": category["platform_fit"],
                    "target_user": category["target_user"],
                    "monetization": category["monetization"],
                    "mvp": category["mvp"],
                    "matched_keywords": matched_keywords,
                    "post_count": len(evidence),
                    "subreddit_count": len(unique_subreddits),
                    "evidence": evidence[:5],
                }
            )

        opportunities.sort(
            key=lambda item: (
                item["score"],
                item["post_count"],
                item["subreddit_count"],
            ),
            reverse=True,
        )

        return {
            "snapshot": current,
            "previous_snapshot": radar["previous_snapshot"],
            "opportunities": opportunities[:top_n],
        }

    def export_markdown(self, report, output_path=None):
        """Write an Opportunity Radar report as Markdown."""
        output_path = output_path or self._default_output_path()
        self._ensure_parent_dir(output_path)

        snapshot = report["snapshot"]
        previous = report.get("previous_snapshot")
        lines = [
            "# ReddTrender Opportunity Radar",
            "",
            f"- Snapshot: #{snapshot['id']} ({snapshot['created_at']})",
            f"- Posts: {snapshot['post_count']}",
            f"- Previous snapshot: #{previous['id']} ({previous['created_at']})" if previous else "- Previous snapshot: none",
            "",
            "## Ranked Opportunities",
            "",
            "| # | Opportunity | Score | Confidence | Platform | Monetization |",
            "|---|-------------|-------|------------|----------|--------------|",
        ]

        for index, opportunity in enumerate(report["opportunities"], 1):
            lines.append(
                "| {index} | {name} | {score:.2f} | {confidence} | {platform} | {monetization} |".format(
                    index=index,
                    name=self._escape_md(opportunity["name"]),
                    score=opportunity["score"],
                    confidence=self._escape_md(opportunity["confidence"]),
                    platform=self._escape_md(opportunity["platform_fit"]),
                    monetization=self._escape_md(opportunity["monetization"]),
                )
            )

        for opportunity in report["opportunities"]:
            lines.extend(
                [
                    "",
                    f"## {opportunity['name']}",
                    "",
                    f"- Key: `{opportunity['key']}`",
                    f"- Target user: {opportunity['target_user']}",
                    f"- MVP: {opportunity['mvp']}",
                    f"- Matched keywords: {', '.join(opportunity['matched_keywords'])}",
                    f"- Evidence: {opportunity['post_count']} posts across {opportunity['subreddit_count']} subreddits",
                    "",
                    "| Subreddit | Momentum | Score | Comments | Matched | Post |",
                    "|-----------|----------|-------|----------|---------|------|",
                ]
            )
            for item in opportunity["evidence"]:
                lines.append(
                    "| {subreddit} | {momentum:.2f} | {score} | {comments} | {keywords} | [{title}]({url}) |".format(
                        subreddit=self._escape_md(item["subreddit"]),
                        momentum=item["momentum_score"],
                        score=item["score"],
                        comments=item["num_comments"],
                        keywords=self._escape_md(", ".join(item["matched_keywords"])),
                        title=self._escape_md(item["title"]),
                        url=item["url"],
                    )
                )

        if not report["opportunities"]:
            lines.append("No scored opportunities found for this snapshot.")

        with open(output_path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

        return output_path

    def _select_categories(self, category_key):
        if not category_key:
            return self.categories
        if category_key not in self.categories:
            known = ", ".join(sorted(self.categories))
            raise ValueError(f"Bilinmeyen opportunity category: {category_key}. Secenekler: {known}")
        return {category_key: self.categories[category_key]}

    def _evidence_for_category(self, category, posts):
        evidence = []
        for post in posts:
            matched = self._matched_keywords(category["keywords"], post)
            if not matched:
                continue
            contribution = self._post_contribution(post, matched)
            evidence.append(
                {
                    "id": post["id"],
                    "title": post["title"],
                    "subreddit": post["subreddit"],
                    "url": post["url"],
                    "score": int(post.get("score") or 0),
                    "num_comments": int(post.get("num_comments") or 0),
                    "momentum_score": float(post.get("momentum_score") or 0),
                    "is_new": bool(post.get("is_new")),
                    "matched_keywords": matched,
                    "contribution": contribution,
                }
            )

        evidence.sort(
            key=lambda item: (
                item["contribution"],
                item["momentum_score"],
                item["score"],
                item["num_comments"],
            ),
            reverse=True,
        )
        return evidence

    @classmethod
    def _matched_keywords(cls, keywords, post):
        text = " ".join(
            [
                str(post.get("title", "")),
                str(post.get("selftext", "")),
                str(post.get("subreddit", "")),
                str(post.get("link_flair_text", "")),
            ]
        ).lower()
        return [
            keyword
            for keyword in keywords
            if cls._contains_keyword(text, keyword.lower())
        ]

    @staticmethod
    def _contains_keyword(text, keyword):
        if len(keyword) <= 3 and keyword.replace("-", "").isalnum():
            return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
        return keyword in text

    @staticmethod
    def _post_contribution(post, matched_keywords):
        score = int(post.get("score") or 0)
        comments = int(post.get("num_comments") or 0)
        momentum = float(post.get("momentum_score") or 0)
        relevance = min(42, len(matched_keywords) * 12)
        activity = min(32, (score + comments * 2) / 250)
        velocity = min(45, momentum / 25)
        novelty = 6 if post.get("is_new") else 0
        return round(relevance + activity + velocity + novelty, 2)

    @staticmethod
    def _score_category(evidence, matched_keywords, unique_subreddits):
        top_evidence_score = sum(item["contribution"] for item in evidence[:5])
        breadth = min(24, len(unique_subreddits) * 5 + min(len(evidence), 9))
        keyword_breadth = min(18, len(matched_keywords) * 1.75)
        return round(top_evidence_score + breadth + keyword_breadth, 2)

    @staticmethod
    def _confidence(score, evidence, unique_subreddits):
        if score >= 180 and len(evidence) >= 3 and len(unique_subreddits) >= 2:
            return "high"
        if score >= 90 or len(evidence) >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _default_output_path():
        os.makedirs(config.REPORT_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return os.path.join(config.REPORT_DIR, f"opportunity-radar-{stamp}.md")

    @staticmethod
    def _ensure_parent_dir(path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @staticmethod
    def _escape_md(value):
        return str(value or "").replace("|", "\\|").replace("\n", " ")
