"""
Static subreddit analytics dashboard for ReddTrender snapshots.
"""

import html
import os
from collections import Counter
from datetime import datetime, timezone

import config
from storage import TrendStore
from trend_radar import TrendRadarService


class SubredditAnalyticsDashboard:
    """Builds an HTML dashboard from local TrendStore snapshots."""

    def __init__(self, store=None):
        self.store = store or TrendStore()

    def build(self, snapshot_id=None, history_limit=8, top_n=10):
        """Return a dashboard data model for the selected or latest snapshot."""
        current = self.store.get_snapshot(snapshot_id)
        if not current:
            raise ValueError("Dashboard icin snapshot yok. Once --snapshot calistirin.")

        snapshots = self._history_for(current, history_limit)
        previous = self.store.get_previous_snapshot(current["id"])
        current_metrics = self.store.get_subreddit_metrics(current["id"])
        previous_metrics = self.store.get_subreddit_metrics(previous["id"]) if previous else []
        metric_deltas = TrendRadarService._compare_subreddits(current_metrics, previous_metrics)
        radar = TrendRadarService(store=self.store).build_radar(current["id"], top_n=top_n)
        history_rows = self._build_history_rows(snapshots)
        top_subreddits = metric_deltas[:top_n]

        return {
            "snapshot": current,
            "previous_snapshot": previous,
            "snapshots": snapshots,
            "kpis": self._build_kpis(current, previous, top_subreddits, history_rows),
            "top_subreddits": top_subreddits,
            "heat_series": self._build_heat_series(snapshots, top_subreddits[:6]),
            "history_rows": history_rows,
            "keyword_summary": self._build_keyword_summary(snapshots),
            "latest_alerts": self.store.get_keyword_alerts(current["id"])[:top_n],
            "top_posts": radar["top_posts"][:top_n],
            "recommendations": self._build_recommendations(top_subreddits, radar["top_posts"], history_rows),
        }

    def export_html(self, dashboard, output_path=None):
        """Write the dashboard as a standalone HTML document."""
        output_path = output_path or self._default_output_path()
        self._ensure_parent_dir(output_path)

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(self.render_html(dashboard))

        return output_path

    def render_html(self, dashboard):
        snapshot = dashboard["snapshot"]
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ReddTrender Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f4ef;
      --surface: #ffffff;
      --ink: #1e2025;
      --muted: #69707d;
      --line: #d8d2ca;
      --red: #d63f2f;
      --green: #2e7d56;
      --blue: #2d5f8b;
      --gold: #a96f16;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: 30px; line-height: 1.1; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    h3 {{ font-size: 14px; margin-bottom: 6px; }}
    .meta {{ color: var(--muted); margin-top: 8px; }}
    .stamp {{ color: var(--muted); text-align: right; }}
    .grid {{
      display: grid;
      gap: 14px;
      margin-top: 18px;
    }}
    .kpis {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .two {{ grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr); }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .kpi-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .kpi-value {{ font-size: 27px; font-weight: 750; margin-top: 5px; }}
    .kpi-note {{ color: var(--muted); margin-top: 4px; min-height: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    tr:last-child td {{ border-bottom: 0; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .delta-pos {{ color: var(--green); font-weight: 700; }}
    .delta-neg {{ color: var(--red); font-weight: 700; }}
    .bar-track {{ height: 8px; background: #ece7df; border-radius: 999px; overflow: hidden; margin-top: 5px; }}
    .bar-fill {{ height: 100%; background: var(--red); }}
    .spark {{
      width: 100%;
      height: 180px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfaf7;
    }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 10px; color: var(--muted); }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      background: currentColor;
      margin-right: 6px;
    }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 9px;
      background: #fbfaf7;
      color: var(--ink);
    }}
    .muted {{ color: var(--muted); }}
    .rec-list {{ display: grid; gap: 10px; }}
    .rec {{ border-left: 3px solid var(--gold); padding-left: 10px; }}
    @media (max-width: 860px) {{
      header {{ display: block; }}
      .stamp {{ text-align: left; margin-top: 10px; }}
      .kpis, .two {{ grid-template-columns: 1fr; }}
      .shell {{ width: min(100vw - 20px, 1180px); padding-top: 18px; }}
      h1 {{ font-size: 24px; }}
      .kpi-value {{ font-size: 23px; }}
      th, td {{ padding: 8px 6px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>ReddTrender Analytics Dashboard</h1>
        <p class="meta">Snapshot #{self._e(snapshot["id"])} · {self._e(snapshot["created_at"])} · {self._e(snapshot.get("label") or "etiketsiz")}</p>
      </div>
      <div class="stamp">Uretildi<br>{self._e(generated_at)}</div>
    </header>

    <section class="grid kpis">
      {self._render_kpis(dashboard["kpis"])}
    </section>

    <section class="grid two">
      <div class="panel">
        <h2>Subreddit Isı Liderleri</h2>
        {self._render_subreddit_table(dashboard["top_subreddits"])}
      </div>
      <div class="panel">
        <h2>Operasyon Notları</h2>
        {self._render_recommendations(dashboard["recommendations"])}
      </div>
    </section>

    <section class="grid two">
      <div class="panel">
        <h2>Isı Geçmişi</h2>
        {self._render_heat_chart(dashboard["heat_series"])}
      </div>
      <div class="panel">
        <h2>Keyword Hareketi</h2>
        {self._render_keyword_summary(dashboard["keyword_summary"])}
      </div>
    </section>

    <section class="grid two">
      <div class="panel">
        <h2>Momentum Gönderileri</h2>
        {self._render_posts_table(dashboard["top_posts"])}
      </div>
      <div class="panel">
        <h2>Son Keyword Alarmları</h2>
        {self._render_alerts_table(dashboard["latest_alerts"])}
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Snapshot Geçmişi</h2>
        {self._render_history_table(dashboard["history_rows"])}
      </div>
    </section>
  </main>
</body>
</html>
"""

    def _history_for(self, current, history_limit):
        snapshots = self.store.list_snapshots(limit=max(history_limit, 1))
        if all(snapshot["id"] != current["id"] for snapshot in snapshots):
            snapshots.append(current)
        snapshots.sort(key=lambda item: (item["created_at"], item["id"]))
        return snapshots[-history_limit:]

    def _build_kpis(self, current, previous, top_subreddits, history_rows):
        latest_heat = sum(row["heat_index"] for row in top_subreddits)
        previous_posts = previous["post_count"] if previous else 0
        post_delta = current["post_count"] - previous_posts if previous else current["post_count"]
        tracked_subreddits = len(top_subreddits)
        alert_total = history_rows[-1]["alert_count"] if history_rows else 0
        hottest = top_subreddits[0]["subreddit"] if top_subreddits else "n/a"
        heat_delta = sum(row["heat_delta"] for row in top_subreddits)

        return [
            {"label": "Gonderi", "value": current["post_count"], "note": f"{post_delta:+d} onceki snapshot"},
            {"label": "Takip Edilen Subreddit", "value": tracked_subreddits, "note": f"lider: {hottest}"},
            {"label": "Toplam Isi", "value": latest_heat, "note": f"{heat_delta:+d} isi farki"},
            {"label": "Keyword Alarmi", "value": alert_total, "note": "son snapshot"},
        ]

    def _build_history_rows(self, snapshots):
        rows = []
        for snapshot in snapshots:
            metrics = self.store.get_subreddit_metrics(snapshot["id"])
            alerts = self.store.get_keyword_alerts(snapshot["id"])
            rows.append(
                {
                    "id": snapshot["id"],
                    "created_at": snapshot["created_at"],
                    "post_count": snapshot["post_count"],
                    "subreddit_count": len(metrics),
                    "total_heat": sum(metric["heat_index"] for metric in metrics),
                    "alert_count": len(alerts),
                }
            )
        return rows

    def _build_heat_series(self, snapshots, top_subreddits):
        names = [metric["subreddit"] for metric in top_subreddits]
        series = {name: [] for name in names}
        labels = []

        for snapshot in snapshots:
            labels.append(f"#{snapshot['id']}")
            metrics = {
                metric["subreddit"]: metric["heat_index"]
                for metric in self.store.get_subreddit_metrics(snapshot["id"])
            }
            for name in names:
                series[name].append(metrics.get(name, 0))

        return {"labels": labels, "series": series}

    def _build_keyword_summary(self, snapshots):
        counter = Counter()
        for snapshot in snapshots:
            for alert in self.store.get_keyword_alerts(snapshot["id"]):
                counter[alert["keyword"]] += 1
        return counter.most_common(12)

    @staticmethod
    def _build_recommendations(top_subreddits, top_posts, history_rows):
        recommendations = []
        if top_subreddits:
            leader = top_subreddits[0]
            recommendations.append(
                {
                    "title": f"{leader['subreddit']} isiyi tasiyor",
                    "body": f"Bu snapshot'ta isi farki {leader['heat_delta']:+d}. En iyi gonderiyi rapora veya haftalik ozete alin.",
                }
            )
        if top_posts:
            post = top_posts[0]
            recommendations.append(
                {
                    "title": "En yuksek momentumlu konu",
                    "body": f"{post['subreddit']} icinde {post['momentum_score']} momentum: {post['title']}",
                }
            )
        if len(history_rows) >= 2:
            previous = history_rows[-2]["total_heat"]
            latest = history_rows[-1]["total_heat"]
            delta = latest - previous
            direction = "artti" if delta >= 0 else "azaldi"
            recommendations.append(
                {
                    "title": "Genel hareket",
                    "body": f"Toplam isi onceki snapshot'a gore {abs(delta)} puan {direction}.",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "title": "Ilk veri seti hazir",
                    "body": "Bir sonraki snapshot'tan sonra dashboard ivme ve farklari daha net gosterecek.",
                }
            )
        return recommendations

    def _render_kpis(self, kpis):
        return "\n".join(
            f"""
      <div class="panel">
        <div class="kpi-label">{self._e(kpi["label"])}</div>
        <div class="kpi-value">{self._format_number(kpi["value"])}</div>
        <div class="kpi-note">{self._e(kpi["note"])}</div>
      </div>"""
            for kpi in kpis
        )

    def _render_subreddit_table(self, rows):
        if not rows:
            return '<p class="muted">Subreddit metrigi yok.</p>'
        max_heat = max(row["heat_index"] for row in rows) or 1
        body = []
        for row in rows:
            width = min(100, int((row["heat_index"] / max_heat) * 100))
            body.append(
                "<tr>"
                f"<td>{self._e(row['subreddit'])}<div class=\"bar-track\"><div class=\"bar-fill\" style=\"width:{width}%\"></div></div></td>"
                f"<td class=\"num\">{self._format_number(row['heat_index'])}</td>"
                f"<td class=\"num {self._delta_class(row['heat_delta'])}\">{row['heat_delta']:+d}</td>"
                f"<td class=\"num\">{self._format_number(row['total_comments'])}</td>"
                f"<td>{self._link(row['top_post_title'], row['top_post_url'])}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Subreddit</th><th class=\"num\">Isi</th>"
            "<th class=\"num\">Fark</th><th class=\"num\">Yorum</th><th>En iyi konu</th>"
            "</tr></thead><tbody>"
            + "".join(body)
            + "</tbody></table>"
        )

    def _render_recommendations(self, recommendations):
        return '<div class="rec-list">' + "".join(
            f'<div class="rec"><h3>{self._e(item["title"])}</h3><p class="muted">{self._e(item["body"])}</p></div>'
            for item in recommendations
        ) + "</div>"

    def _render_heat_chart(self, heat_series):
        labels = heat_series["labels"]
        series = heat_series["series"]
        if not labels or not series:
            return '<p class="muted">Grafik icin yeterli veri yok.</p>'

        colors = ["#d63f2f", "#2e7d56", "#2d5f8b", "#a96f16", "#6e4aa5", "#4d7f7a"]
        values = [value for points in series.values() for value in points]
        max_value = max(values) if values else 1
        max_value = max(max_value, 1)
        width = 720
        height = 180
        pad = 24
        x_step = (width - pad * 2) / max(len(labels) - 1, 1)
        chart_parts = [
            f'<svg class="spark" viewBox="0 0 {width} {height}" role="img" aria-label="Subreddit heat history">',
            f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="#d8d2ca"/>',
        ]

        for index, (name, points) in enumerate(series.items()):
            color = colors[index % len(colors)]
            coords = []
            for point_index, value in enumerate(points):
                x = pad + point_index * x_step
                y = height - pad - ((value / max_value) * (height - pad * 2))
                coords.append(f"{x:.1f},{y:.1f}")
            chart_parts.append(
                f'<polyline points="{" ".join(coords)}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
            )
            for coord in coords:
                x, y = coord.split(",")
                chart_parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"/>')

        for index, label in enumerate(labels):
            x = pad + index * x_step
            chart_parts.append(f'<text x="{x:.1f}" y="{height - 6}" text-anchor="middle" font-size="11" fill="#69707d">{self._e(label)}</text>')

        chart_parts.append("</svg>")
        legend = '<div class="legend">' + "".join(
            f'<span style="color:{colors[index % len(colors)]}">{self._e(name)}</span>'
            for index, name in enumerate(series.keys())
        ) + "</div>"
        return "".join(chart_parts) + legend

    def _render_keyword_summary(self, summary):
        if not summary:
            return '<p class="muted">Secili aralikta keyword alarmi yok.</p>'
        max_count = max(count for _, count in summary) or 1
        chips = []
        for keyword, count in summary:
            width = min(100, int((count / max_count) * 100))
            chips.append(
                f'<div class="chip">{self._e(keyword)} · {count}<div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div></div>'
            )
        return '<div class="chips">' + "".join(chips) + "</div>"

    def _render_posts_table(self, posts):
        if not posts:
            return '<p class="muted">Momentum gonderisi yok.</p>'
        rows = []
        for post in posts:
            rows.append(
                "<tr>"
                f"<td>{self._link(post['title'], post['url'])}<div class=\"muted\">{self._e(post['subreddit'])}</div></td>"
                f"<td class=\"num\">{post['momentum_score']}</td>"
                f"<td class=\"num {self._delta_class(post['score_delta'])}\">{post['score_delta']:+d}</td>"
                f"<td class=\"num {self._delta_class(post['comment_delta'])}\">{post['comment_delta']:+d}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Konu</th><th class=\"num\">Momentum</th>"
            "<th class=\"num\">Skor</th><th class=\"num\">Yorum</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _render_alerts_table(self, alerts):
        if not alerts:
            return '<p class="muted">Son snapshot icin alert yok.</p>'
        rows = []
        for alert in alerts:
            rows.append(
                "<tr>"
                f"<td>{self._e(alert['keyword'])}</td>"
                f"<td>{self._e(alert['subreddit'])}</td>"
                f"<td>{self._link(alert['title'], alert['url'])}</td>"
                f"<td class=\"num\">{self._format_number(alert['score'])}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Keyword</th><th>Subreddit</th><th>Konu</th>"
            "<th class=\"num\">Skor</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _render_history_table(self, rows):
        if not rows:
            return '<p class="muted">Snapshot gecmisi yok.</p>'
        body = []
        for row in rows:
            body.append(
                "<tr>"
                f"<td>#{row['id']}</td>"
                f"<td>{self._e(row['created_at'])}</td>"
                f"<td class=\"num\">{self._format_number(row['post_count'])}</td>"
                f"<td class=\"num\">{self._format_number(row['subreddit_count'])}</td>"
                f"<td class=\"num\">{self._format_number(row['total_heat'])}</td>"
                f"<td class=\"num\">{self._format_number(row['alert_count'])}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>ID</th><th>Zaman</th><th class=\"num\">Post</th>"
            "<th class=\"num\">Subreddit</th><th class=\"num\">Isi</th><th class=\"num\">Alert</th>"
            "</tr></thead><tbody>"
            + "".join(body)
            + "</tbody></table>"
        )

    @staticmethod
    def _ensure_parent_dir(path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @staticmethod
    def _default_output_path():
        os.makedirs(config.REPORT_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return os.path.join(config.REPORT_DIR, f"subreddit-dashboard-{stamp}.html")

    @staticmethod
    def _format_number(value):
        if isinstance(value, float):
            return f"{value:,.2f}"
        return f"{int(value):,}"

    @staticmethod
    def _delta_class(value):
        return "delta-pos" if value >= 0 else "delta-neg"

    def _link(self, label, url):
        label = self._e(label or "link")
        url = self._e(url or "#")
        return f'<a href="{url}" target="_blank" rel="noreferrer">{label}</a>'

    @staticmethod
    def _e(value):
        return html.escape(str(value), quote=True)
