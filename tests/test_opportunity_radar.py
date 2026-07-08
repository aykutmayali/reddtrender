import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from opportunity_radar import OpportunityRadarService
from storage import TrendStore


def make_post(post_id, title, score, comments, subreddit="r/test", selftext="", hours_old=2):
    created = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    return {
        "id": post_id,
        "title": title,
        "subreddit": subreddit,
        "author": "tester",
        "score": score,
        "upvote_ratio": 0.9,
        "num_comments": comments,
        "url": f"https://reddit.com/r/test/comments/{post_id}",
        "created_utc": created.timestamp(),
        "selftext": selftext,
        "is_self": True,
        "link_flair_text": "",
        "over_18": False,
        "spoiler": False,
        "stickied": False,
        "trend_category": "Test",
    }


class OpportunityRadarServiceTest(unittest.TestCase):
    def test_build_ranks_matching_opportunities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrendStore(db_path=os.path.join(tmpdir, "opportunity.db"))
            store.create_snapshot(
                [
                    make_post(
                        "p1",
                        "Moderators need better AI spam and bot detection",
                        100,
                        20,
                        "r/modhelp",
                    )
                ],
                keywords=["ai"],
            )
            snapshot_id = store.create_snapshot(
                [
                    make_post(
                        "p1",
                        "Moderators need better AI spam and bot detection",
                        180,
                        45,
                        "r/modhelp",
                    ),
                    make_post(
                        "p2",
                        "Subreddit analytics dashboard for weekly trend reports",
                        90,
                        14,
                        "r/community",
                    ),
                ],
                keywords=["ai", "analytics"],
            )

            service = OpportunityRadarService(store=store)
            report = service.build(snapshot_id=snapshot_id, top_n=5)
            keys = [opportunity["key"] for opportunity in report["opportunities"]]

            self.assertIn("ai-content-moderation", keys)
            self.assertIn("subreddit-analytics", keys)
            ai_opportunity = next(
                item for item in report["opportunities"] if item["key"] == "ai-content-moderation"
            )
            self.assertGreater(ai_opportunity["score"], 0)
            self.assertEqual(ai_opportunity["evidence"][0]["id"], "p1")

    def test_export_markdown_writes_opportunity_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrendStore(db_path=os.path.join(tmpdir, "opportunity.db"))
            snapshot_id = store.create_snapshot(
                [
                    make_post(
                        "p1",
                        "Daily trivia game with leaderboard and streak rewards",
                        250,
                        80,
                        "r/games",
                    )
                ],
                keywords=["game"],
            )

            service = OpportunityRadarService(store=store)
            report = service.build(snapshot_id=snapshot_id, top_n=5)
            output_path = os.path.join(tmpdir, "opportunity.md")
            service.export_markdown(report, output_path)

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as file:
                content = file.read()
            self.assertIn("ReddTrender Opportunity Radar", content)
            self.assertIn("Daily Community Games", content)
            self.assertIn("Daily trivia game", content)


if __name__ == "__main__":
    unittest.main()
