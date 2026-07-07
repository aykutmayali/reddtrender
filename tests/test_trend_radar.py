import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from storage import TrendStore
from trend_radar import TrendRadarService


def make_post(post_id, title, score, comments, subreddit="r/test", hours_old=2):
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
        "selftext": "",
        "is_self": True,
        "link_flair_text": "",
        "over_18": False,
        "spoiler": False,
        "stickied": False,
        "trend_category": "Test",
    }


class TrendRadarServiceTest(unittest.TestCase):
    def test_build_radar_compares_latest_snapshot_with_previous(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrendStore(db_path=os.path.join(tmpdir, "radar.db"))
            store.create_snapshot(
                [make_post("p1", "AI tools launch", 100, 10)],
                keywords=["ai"],
            )
            second_id = store.create_snapshot(
                [
                    make_post("p1", "AI tools launch", 140, 25),
                    make_post("p2", "Privacy update", 50, 8, subreddit="r/privacy"),
                ],
                keywords=["privacy"],
            )

            service = TrendRadarService(store=store)
            report = service.build_radar(snapshot_id=second_id, top_n=5)

            tracked = next(post for post in report["top_posts"] if post["id"] == "p1")
            self.assertEqual(tracked["score_delta"], 40)
            self.assertEqual(tracked["comment_delta"], 15)
            self.assertFalse(tracked["is_new"])
            self.assertEqual(report["previous_snapshot"]["id"], 1)
            self.assertEqual(report["alerts"][0]["keyword"], "privacy")

    def test_export_markdown_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrendStore(db_path=os.path.join(tmpdir, "radar.db"))
            snapshot_id = store.create_snapshot(
                [make_post("p1", "Security discussion", 25, 4)],
                keywords=["security"],
            )
            service = TrendRadarService(store=store)
            report = service.build_radar(snapshot_id=snapshot_id, top_n=5)

            output_path = os.path.join(tmpdir, "report.md")
            service.export_markdown(report, output_path)

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as file:
                content = file.read()
            self.assertIn("ReddTrender Trend Radar", content)
            self.assertIn("Security discussion", content)


if __name__ == "__main__":
    unittest.main()
