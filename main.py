#!/usr/bin/env python3
"""
ReddTrender - Reddit Trend Analizi Uygulaması
Reddit API'den trend bilgilerini çeker ve terminalde görsel olarak sunar.

Kullanım:
    python main.py                  # Genel trend özeti
    python main.py --hot            # Popüler gönderiler
    python main.py --rising         # Yükselişte olan gönderiler
    python main.py --top            # Günün en çok oy alanları
    python main.py --subreddits     # Subreddit bazlı trend analizi
    python main.py --search <query> # Reddit'te arama
    python main.py --topics         # Sıcak konular ve kelime analizi
"""

import argparse
import sys
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from reddit_client import RedditClient
from trends import TrendAnalyzer
from storage import TrendStore
from trend_radar import TrendRadarService
from analytics_dashboard import SubredditAnalyticsDashboard
import config


console = Console()


def print_banner():
    """Uygulama başlığını göster."""
    banner = Text()
    banner.append("Redd", style="bold red")
    banner.append("Trender", style="bold orange3")
    banner.append(" ─ Trend Analizi", style="dim")
    console.print(Panel(banner, border_style="red", padding=(1, 2)))
    console.print()


def format_score(score):
    """Skoru okunabilir formata çevir (örn: 12.5k)."""
    if score >= 1_000_000:
        return f"{score / 1_000_000:.1f}M"
    if score >= 1_000:
        return f"{score / 1_000:.1f}k"
    return str(score)


def format_time(utc_timestamp):
    """UTC timestamp'i okunabilir formata çevir."""
    if not utc_timestamp:
        return ""
    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return f"{int(diff.total_seconds() / 60)}dk önce"
    if hours < 24:
        return f"{int(hours)}sa önce"
    return f"{int(hours / 24)}g önce"


def format_delta(value):
    """Pozitif/negatif farkları okunabilir göster."""
    return f"{value:+}"


def parse_csv_arg(value):
    """Virgülle ayrılmış CLI değerini listeye çevir."""
    if not value or value == "default":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def create_posts_table(posts, title="Gönderiler", max_rows=25):
    """Gönderiler için zengin tablo oluştur."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Subreddit", style="magenta", width=12)
    table.add_column("Başlık", style="white", min_width=30, max_width=60)
    table.add_column("Skor", style="green", width=8, justify="right")
    table.add_column("Yorumlar", style="yellow", width=8, justify="right")
    table.add_column("Süre", style="dim", width=10, justify="right")

    for i, post in enumerate(posts[:max_rows], 1):
        flair = f" [{post['link_flair_text']}]" if post.get("link_flair_text") else ""
        title_text = post["title"][:58] + ("..." if len(post["title"]) > 58 else "")

        table.add_row(
            str(i),
            post["subreddit"],
            f"{title_text}{flair}",
            format_score(post["score"]),
            format_score(post["num_comments"]),
            format_time(post.get("created_utc")),
        )

    return table


def show_hot(limit=None):
    """Popüler gönderileri göster."""
    console.print("[bold cyan]📊 Popüler Gönderiler (Hot)[/bold cyan]\n")
    client = RedditClient()
    limit = limit or config.DEFAULT_LIMIT
    posts = client.get_popular(limit=limit)

    if not posts:
        console.print("[red]Veri alınamadı.[/red]")
        return

    console.print(create_posts_table(posts, "Reddit Popüler", max_rows=limit))


def show_rising(limit=None):
    """Yükselişte olan gönderileri göster."""
    console.print("[bold cyan]📈 Yükselişte Olan Gönderiler (Rising)[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    limit = limit or config.DEFAULT_LIMIT
    rising = analyzer.get_rising_trends(limit=limit)

    if not rising:
        console.print("[red]Veri alınamadı.[/red]")
        return

    table = Table(
        title="Yükselişte Olan Gönderiler",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Subreddit", style="magenta", width=12)
    table.add_column("Başlık", style="white", min_width=25, max_width=55)
    table.add_column("Skor", style="green", width=8, justify="right")
    table.add_column("Yorum", style="yellow", width=8, justify="right")
    table.add_column("Viral", style="bold red", width=8, justify="right")
    table.add_column("Etkileşim", style="cyan", width=10, justify="right")

    for i, post in enumerate(rising[:limit], 1):
        table.add_row(
            str(i),
            post["subreddit"],
            post["title"][:53] + ("..." if len(post["title"]) > 53 else ""),
            format_score(post["score"]),
            format_score(post["num_comments"]),
            format_score(post["viral_score"]),
            f"%{post['engagement_rate']}",
        )

    console.print(table)


def show_top(time_filter="day", limit=None):
    """En çok oy alan gönderileri göster."""
    labels = {"hour": "Saat", "day": "Gün", "week": "Hafta", "month": "Ay", "year": "Yıl"}
    label = labels.get(time_filter, "Gün")

    console.print(f"[bold cyan]🏆 {label}ün En Çok Oy Alan Gönderileri[/bold cyan]\n")
    client = RedditClient()
    limit = limit or config.DEFAULT_LIMIT
    posts = client.get_top("popular", time_filter=time_filter, limit=limit)

    if not posts:
        console.print("[red]Veri alınamadı.[/red]")
        return

    console.print(create_posts_table(posts, f"{label}ün En İyileri", max_rows=limit))


def show_subreddit_trends(subreddits=None, sort="hot", limit=10):
    """Subreddit bazlı trend analizi yap."""
    if subreddits:
        sub_list = parse_csv_arg(subreddits)
    else:
        sub_list = None

    console.print("[bold cyan]🔍 Subreddit Trend Analizi[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    trends = analyzer.get_trending_subreddits(subreddits=sub_list, sort=sort, limit=limit)

    if not trends:
        console.print("[red]Veri alınamadı.[/red]")
        return

    table = Table(
        title="Subreddit Isı Sıralaması",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Subreddit", style="magenta bold", width=16)
    table.add_column("Isı", style="red", width=10, justify="right")
    table.add_column("Toplam Skor", style="green", width=10, justify="right")
    table.add_column("Yorumlar", style="yellow", width=10, justify="right")
    table.add_column("Ort. Skor", style="cyan", width=10, justify="right")
    table.add_column("En İyi Gönderi", style="white", max_width=35)

    for i, trend in enumerate(trends, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))
        top_title = trend["top_post_title"][:33] + ("..." if len(trend["top_post_title"]) > 33 else "")

        table.add_row(
            medal,
            trend["subreddit"],
            format_score(trend["heat_index"]),
            format_score(trend["total_score"]),
            format_score(trend["total_comments"]),
            format_score(trend["avg_score"]),
            top_title,
        )

    console.print(table)


def show_topics(limit=None):
    """Sıcak konuları ve kelime analizini göster."""
    console.print("[bold cyan]💡 Sıcak Konular ve Kelime Analizi[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    limit = limit or 50
    data = analyzer.get_hot_topics(limit=limit)

    if not data["posts"]:
        console.print("[red]Veri alınamadı.[/red]")
        return

    # Kelime frekans tablosu
    if data["top_words"]:
        word_table = Table(
            title="En Sık Kullanılan Kelimeler",
            box=box.SIMPLE,
            header_style="bold green",
            padding=(0, 1),
        )
        word_table.add_column("Kelime", style="white")
        word_table.add_column("Frekans", style="bold green", justify="right")

        for word, count in data["top_words"]:
            bar = "█" * min(count, 20)
            word_table.add_row(word, f"{count} {bar}")

        # Subreddit dağılımı
        sub_table = Table(
            title="Subreddit Dağılımı",
            box=box.SIMPLE,
            header_style="bold magenta",
            padding=(0, 1),
        )
        sub_table.add_column("Subreddit", style="magenta")
        sub_table.add_column("Gönderi", style="bold", justify="right")

        for sub, count in data["top_subreddits"]:
            sub_table.add_row(sub, str(count))

        console.print(Columns([word_table, sub_table], expand=True))

    console.print()
    console.print(create_posts_table(data["posts"], "Popüler Gönderiler", max_rows=min(limit, 25)))


def show_daily_summary():
    """Günlük trend özetini göster."""
    console.print("[bold cyan]📋 Günlük Trend Özeti[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    summary = analyzer.get_daily_summary()

    if not summary["posts"]:
        console.print("[red]Veri alınamadı.[/red]")
        return

    # Özet bilgi paneli
    info = Text()
    info.append(f"Zaman: ", style="bold")
    info.append(f"{summary['timestamp']}\n", style="cyan")
    info.append(f"Toplam Benzersiz Gönderi: ", style="bold")
    info.append(f"{summary['total_posts']}\n", style="green")
    info.append(f"Popüler: ", style="bold")
    info.append(f"{summary['popular_count']}  ", style="yellow")
    info.append(f"Yükseliş: ", style="bold")
    info.append(f"{summary['rising_count']}  ", style="red")
    info.append(f"Günün En İyisi: ", style="bold")
    info.append(f"{summary['top_count']}", style="magenta")

    console.print(Panel(info, title="Özet", border_style="blue", padding=(1, 2)))
    console.print()
    console.print(create_posts_table(summary["posts"], "Tüm Trendler (Skora Göre)", max_rows=25))


def search_reddit(query, subreddit=None, limit=None):
    """Reddit'te arama yap ve sonuçları göster."""
    console.print(f"[bold cyan]🔎 Arama: '{query}'[/bold cyan]\n")
    client = RedditClient()
    limit = limit or config.DEFAULT_LIMIT
    posts = client.search(query, subreddit=subreddit, limit=limit)

    if not posts:
        console.print("[yellow]Sonuç bulunamadı.[/yellow]")
        return

    title = f"'{query}' Arama Sonuçları"
    if subreddit:
        title += f" (r/{subreddit})"
    console.print(create_posts_table(posts, title, max_rows=limit))


def collect_trend_snapshot(subreddits=None, limit=None, keywords=None, label=None):
    """Reddit'ten snapshot topla ve yerel veritabanına kaydet."""
    limit = limit or config.DEFAULT_LIMIT
    keyword_list = parse_csv_arg(keywords) if keywords else config.DEFAULT_KEYWORDS
    subreddit_list = parse_csv_arg(subreddits)

    console.print("[bold cyan]📡 Trend snapshot alınıyor...[/bold cyan]\n")
    client = RedditClient()
    service = TrendRadarService(client=client)
    result = service.collect_snapshot(
        subreddits=subreddit_list,
        limit=limit,
        keywords=keyword_list,
        label=label,
    )

    snapshot = result["snapshot"]
    info = Text()
    info.append("Snapshot ID: ", style="bold")
    info.append(f"#{snapshot['id']}\n", style="cyan")
    info.append("Zaman: ", style="bold")
    info.append(f"{snapshot['created_at']}\n", style="green")
    info.append("Gönderi: ", style="bold")
    info.append(f"{snapshot['post_count']}\n", style="yellow")
    info.append("Keyword alarmı: ", style="bold")
    info.append(str(len(result["alerts"])), style="red")
    console.print(Panel(info, title="Kaydedildi", border_style="green", padding=(1, 2)))

    return result


def show_snapshot_history(limit=None):
    """Kayıtlı snapshot geçmişini göster."""
    limit = limit or 10
    store = TrendStore()
    snapshots = store.list_snapshots(limit=limit)

    if not snapshots:
        console.print("[yellow]Henüz kayıtlı snapshot yok.[/yellow]")
        return

    table = Table(
        title="Snapshot Geçmişi",
        box=box.ROUNDED,
        header_style="bold cyan",
        padding=(0, 1),
    )
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Zaman", style="green")
    table.add_column("Kaynak", style="magenta")
    table.add_column("Gönderi", style="yellow", justify="right")
    table.add_column("Etiket", style="white")

    for snapshot in snapshots:
        table.add_row(
            str(snapshot["id"]),
            snapshot["created_at"],
            snapshot["source"],
            str(snapshot["post_count"]),
            snapshot.get("label") or "",
        )

    console.print(table)


def create_radar_table(posts, title="Trend Radar"):
    """Momentum skoruna göre gönderi tablosu oluştur."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Durum", style="magenta", width=8)
    table.add_column("Subreddit", style="magenta", width=12)
    table.add_column("Momentum", style="bold red", width=10, justify="right")
    table.add_column("Δ Skor", style="green", width=9, justify="right")
    table.add_column("Δ Yorum", style="yellow", width=9, justify="right")
    table.add_column("Başlık", style="white", min_width=30, max_width=60)

    for i, post in enumerate(posts, 1):
        title_text = post["title"][:58] + ("..." if len(post["title"]) > 58 else "")
        table.add_row(
            str(i),
            "Yeni" if post["is_new"] else "Takip",
            post["subreddit"],
            format_score(post["momentum_score"]),
            format_delta(post["score_delta"]),
            format_delta(post["comment_delta"]),
            title_text,
        )

    return table


def create_subreddit_delta_table(metrics, title="Subreddit Isı Farkı"):
    """Subreddit bazlı heat delta tablosu oluştur."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Subreddit", style="magenta", width=16)
    table.add_column("Isı", style="red", width=10, justify="right")
    table.add_column("Δ Isı", style="bold red", width=10, justify="right")
    table.add_column("Δ Skor", style="green", width=10, justify="right")
    table.add_column("Δ Yorum", style="yellow", width=10, justify="right")
    table.add_column("En İyi Gönderi", style="white", max_width=35)

    for i, metric in enumerate(metrics[:15], 1):
        top_title = metric["top_post_title"][:33] + ("..." if len(metric["top_post_title"]) > 33 else "")
        table.add_row(
            str(i),
            metric["subreddit"],
            format_score(metric["heat_index"]),
            format_delta(metric["heat_delta"]),
            format_delta(metric["score_delta"]),
            format_delta(metric["comment_delta"]),
            top_title,
        )

    return table


def create_alerts_table(alerts, title="Keyword Alarmları"):
    """Keyword eşleşmeleri için tablo oluştur."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Keyword", style="bold red", width=14)
    table.add_column("Subreddit", style="magenta", width=14)
    table.add_column("Skor", style="green", width=8, justify="right")
    table.add_column("Yorum", style="yellow", width=8, justify="right")
    table.add_column("Başlık", style="white", max_width=60)

    for i, alert in enumerate(alerts, 1):
        title_text = alert["title"][:58] + ("..." if len(alert["title"]) > 58 else "")
        table.add_row(
            str(i),
            alert["keyword"],
            alert["subreddit"],
            format_score(alert["score"]),
            format_score(alert["num_comments"]),
            title_text,
        )

    return table


def show_trend_radar(snapshot_id=None, limit=None, export_format=None, output_path=None):
    """Son snapshot'a göre trend radar çıktısını göster."""
    limit = limit or config.DEFAULT_LIMIT
    service = TrendRadarService()
    report = service.build_radar(snapshot_id=snapshot_id, top_n=limit)

    snapshot = report["snapshot"]
    previous = report["previous_snapshot"]
    summary = Text()
    summary.append("Snapshot: ", style="bold")
    summary.append(f"#{snapshot['id']} ({snapshot['created_at']})\n", style="cyan")
    summary.append("Önceki: ", style="bold")
    if previous:
        summary.append(f"#{previous['id']} ({previous['created_at']})\n", style="green")
    else:
        summary.append("yok\n", style="yellow")
    summary.append("Gönderi: ", style="bold")
    summary.append(str(snapshot["post_count"]), style="yellow")

    console.print(Panel(summary, title="Trend Radar", border_style="blue", padding=(1, 2)))
    console.print()
    console.print(create_radar_table(report["top_posts"]))
    console.print()
    console.print(create_subreddit_delta_table(report["subreddit_deltas"]))

    if report["alerts"]:
        console.print()
        console.print(create_alerts_table(report["alerts"][:limit]))

    if export_format:
        if export_format == "markdown":
            path = service.export_markdown(report, output_path)
        else:
            path = service.export_csv(report, output_path)
        console.print(f"\n[green]Rapor yazıldı:[/green] {path}")

    return report


def show_keyword_alerts(snapshot_id=None, limit=None):
    """Son veya seçilen snapshot'ın keyword alarmlarını göster."""
    limit = limit or config.DEFAULT_LIMIT
    store = TrendStore()
    snapshot = store.get_snapshot(snapshot_id)
    if not snapshot:
        console.print("[yellow]Henüz kayıtlı snapshot yok.[/yellow]")
        return

    alerts = store.get_keyword_alerts(snapshot["id"])[:limit]
    if not alerts:
        console.print(f"[yellow]Snapshot #{snapshot['id']} için keyword alarmı yok.[/yellow]")
        return

    console.print(create_alerts_table(alerts, title=f"Keyword Alarmları - Snapshot #{snapshot['id']}"))


def export_dashboard(snapshot_id=None, history_limit=8, limit=None, output_path=None):
    """Yerel snapshot verilerinden HTML dashboard üret."""
    limit = limit or config.DEFAULT_LIMIT
    dashboard = SubredditAnalyticsDashboard()
    data = dashboard.build(
        snapshot_id=snapshot_id,
        history_limit=history_limit,
        top_n=limit,
    )
    path = dashboard.export_html(data, output_path=output_path)

    snapshot = data["snapshot"]
    info = Text()
    info.append("Snapshot: ", style="bold")
    info.append(f"#{snapshot['id']} ({snapshot['created_at']})\n", style="cyan")
    info.append("HTML: ", style="bold")
    info.append(path, style="green")
    console.print(Panel(info, title="Dashboard", border_style="green", padding=(1, 2)))

    return path


def main():
    parser = argparse.ArgumentParser(
        description="ReddTrender - Reddit Trend Analizi Uygulaması",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python main.py                          Genel trend özeti
  python main.py --hot                    Popüler gönderiler
  python main.py --rising                 Yükselişte olanlar (viral analiz)
  python main.py --top                    Günün en çok oy alanları
  python main.py --top --time week        Haftanın en çok oy alanları
  python main.py --subreddits             Varsayılan subreddit trend analizi
  python main.py --subreddits tech,news   Özel subreddit analizi
  python main.py --topics                 Sıcak konular ve kelime analizi
  python main.py --search "python"        Reddit'te arama
  python main.py --search "ai" --sub programming  Subreddit içi arama
  python main.py --snapshot               Trend snapshot kaydet
  python main.py --radar                  Son snapshot için trend radar
  python main.py --snapshot --radar --export markdown
  python main.py --dashboard              HTML analytics dashboard üret
        """,
    )

    parser.add_argument("--hot", action="store_true", help="Popüler gönderileri göster")
    parser.add_argument("--rising", action="store_true", help="Yükselişte olan gönderileri göster")
    parser.add_argument("--top", action="store_true", help="En çok oy alan gönderileri göster")
    parser.add_argument(
        "--time",
        choices=["hour", "day", "week", "month", "year"],
        default="day",
        help="Zaman filtresi (varsayılan: day)",
    )
    parser.add_argument("--subreddits", nargs="?", const="default", help="Subreddit trend analizi (virgülle ayır)")
    parser.add_argument("--topics", action="store_true", help="Sıcak konular ve kelime analizi")
    parser.add_argument("--search", type=str, help="Reddit'te arama yap")
    parser.add_argument("--sub", type=str, help="Aramayı belirli subreddit'te sınırla")
    parser.add_argument("--limit", type=int, help="Maksimum gönderi sayısı")
    parser.add_argument("--snapshot", action="store_true", help="Trend Radar için yerel snapshot kaydet")
    parser.add_argument("--radar", action="store_true", help="Kayıtlı snapshot'lardan momentum raporu göster")
    parser.add_argument("--history", action="store_true", help="Kayıtlı snapshot geçmişini göster")
    parser.add_argument("--alerts", action="store_true", help="Son snapshot keyword alarmlarını göster")
    parser.add_argument("--snapshot-id", type=int, help="Radar/alert için belirli snapshot ID")
    parser.add_argument("--keywords", type=str, help="Keyword alarm listesi (virgülle ayır)")
    parser.add_argument("--label", type=str, help="Snapshot için kısa etiket")
    parser.add_argument("--dashboard", action="store_true", help="Subreddit analytics HTML dashboard üret")
    parser.add_argument(
        "--dashboard-history",
        type=int,
        default=8,
        help="Dashboard için okunacak snapshot sayısı",
    )
    parser.add_argument("--dashboard-output", type=str, help="Dashboard HTML çıktı dosyası")
    parser.add_argument(
        "--export",
        choices=["markdown", "csv"],
        help="Trend Radar raporunu dosyaya aktar",
    )
    parser.add_argument("--output", type=str, help="Export çıktı dosyası")

    args = parser.parse_args()

    print_banner()

    try:
        limit = args.limit or config.DEFAULT_LIMIT

        if args.snapshot:
            result = collect_trend_snapshot(
                subreddits=args.subreddits,
                limit=limit,
                keywords=args.keywords,
                label=args.label,
            )
            if args.radar or args.export:
                console.print()
                show_trend_radar(
                    snapshot_id=result["snapshot"]["id"],
                    limit=limit,
                    export_format=args.export,
                    output_path=args.output,
                )
            if args.dashboard:
                console.print()
                export_dashboard(
                    snapshot_id=result["snapshot"]["id"],
                    history_limit=args.dashboard_history,
                    limit=limit,
                    output_path=args.dashboard_output,
                )
        elif args.dashboard or args.dashboard_output:
            export_dashboard(
                snapshot_id=args.snapshot_id,
                history_limit=args.dashboard_history,
                limit=limit,
                output_path=args.dashboard_output,
            )
        elif args.radar or args.export:
            show_trend_radar(
                snapshot_id=args.snapshot_id,
                limit=limit,
                export_format=args.export,
                output_path=args.output,
            )
        elif args.history:
            show_snapshot_history(limit=limit)
        elif args.alerts:
            show_keyword_alerts(snapshot_id=args.snapshot_id, limit=limit)
        elif args.hot:
            show_hot(limit=limit)
        elif args.rising:
            show_rising(limit=limit)
        elif args.top:
            show_top(args.time, limit=limit)
        elif args.subreddits is not None:
            subs = None if args.subreddits == "default" else args.subreddits
            show_subreddit_trends(subreddits=subs, limit=limit)
        elif args.topics:
            show_topics(limit=limit)
        elif args.search:
            search_reddit(args.search, subreddit=args.sub, limit=limit)
        else:
            show_daily_summary()

    except ValueError as e:
        console.print(f"\n[bold red]Hata:[/bold red] {e}")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"\n[bold red]Bağlantı Hatası:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Çıkış yapıldı.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
