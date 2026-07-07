import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from analytics_dashboard import SubredditAnalyticsDashboard
from storage import TrendStore


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


class SubredditAnalyticsDashboardTest(unittest.TestCase):
    def test_dashboard_model_and_html_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrendStore(db_path=os.path.join(tmpdir, "dashboard.db"))
            store.create_snapshot(
                [
                    make_post("p1", "AI tools launch", 100, 10, "r/ai"),
                    make_post("p2", "Python package", 40, 6, "r/python"),
                ],
                keywords=["ai", "python"],
            )
            snapshot_id = store.create_snapshot(
                [
                    make_post("p1", "AI tools launch", 150, 24, "r/ai"),
                    make_post("p3", "Security privacy thread", 80, 12, "r/security"),
                ],
                keywords=["security", "privacy"],
            )

            dashboard = SubredditAnalyticsDashboard(store=store)
            data = dashboard.build(snapshot_id=snapshot_id, history_limit=5, top_n=5)

            self.assertEqual(data["snapshot"]["id"], snapshot_id)
            self.assertGreaterEqual(len(data["top_subreddits"]), 2)
            keywords = [keyword for keyword, _count in data["keyword_summary"]]
            self.assertIn("security", keywords)

            output_path = os.path.join(tmpdir, "dashboard.html")
            dashboard.export_html(data, output_path)

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as file:
                content = file.read()
            self.assertIn("ReddTrender Analytics Dashboard", content)
            self.assertIn("r/security", content)
            self.assertIn("Security privacy thread", content)


if __name__ == "__main__":
    unittest.main()
