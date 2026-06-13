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


def show_hot():
    """Popüler gönderileri göster."""
    console.print("[bold cyan]📊 Popüler Gönderiler (Hot)[/bold cyan]\n")
    client = RedditClient()
    posts = client.get_popular(limit=25)

    if not posts:
        console.print("[red]Veri alınamadı.[/red]")
        return

    console.print(create_posts_table(posts, "Reddit Popüler"))


def show_rising():
    """Yükselişte olan gönderileri göster."""
    console.print("[bold cyan]📈 Yükselişte Olan Gönderiler (Rising)[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    rising = analyzer.get_rising_trends(limit=25)

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

    for i, post in enumerate(rising[:25], 1):
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


def show_top(time_filter="day"):
    """En çok oy alan gönderileri göster."""
    labels = {"hour": "Saat", "day": "Gün", "week": "Hafta", "month": "Ay", "year": "Yıl"}
    label = labels.get(time_filter, "Gün")

    console.print(f"[bold cyan]🏆 {label}ün En Çok Oy Alan Gönderileri[/bold cyan]\n")
    client = RedditClient()
    posts = client.get_top("popular", time_filter=time_filter, limit=25)

    if not posts:
        console.print("[red]Veri alınamadı.[/red]")
        return

    console.print(create_posts_table(posts, f"{label}ün En İyileri"))


def show_subreddit_trends(subreddits=None, sort="hot"):
    """Subreddit bazlı trend analizi yap."""
    if subreddits:
        sub_list = [s.strip() for s in subreddits.split(",")]
    else:
        sub_list = None

    console.print("[bold cyan]🔍 Subreddit Trend Analizi[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    trends = analyzer.get_trending_subreddits(subreddits=sub_list, sort=sort)

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


def show_topics():
    """Sıcak konuları ve kelime analizini göster."""
    console.print("[bold cyan]💡 Sıcak Konular ve Kelime Analizi[/bold cyan]\n")
    client = RedditClient()
    analyzer = TrendAnalyzer(client)
    data = analyzer.get_hot_topics(limit=50)

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
    console.print(create_posts_table(data["posts"], "Popüler Gönderiler", max_rows=15))


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


def search_reddit(query, subreddit=None):
    """Reddit'te arama yap ve sonuçları göster."""
    console.print(f"[bold cyan]🔎 Arama: '{query}'[/bold cyan]\n")
    client = RedditClient()
    posts = client.search(query, subreddit=subreddit, limit=25)

    if not posts:
        console.print("[yellow]Sonuç bulunamadı.[/yellow]")
        return

    title = f"'{query}' Arama Sonuçları"
    if subreddit:
        title += f" (r/{subreddit})"
    console.print(create_posts_table(posts, title))


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

    args = parser.parse_args()

    print_banner()

    try:
        if args.hot:
            show_hot()
        elif args.rising:
            show_rising()
        elif args.top:
            show_top(args.time)
        elif args.subreddits is not None:
            subs = None if args.subreddits == "default" else args.subreddits
            show_subreddit_trends(subreddits=subs)
        elif args.topics:
            show_topics()
        elif args.search:
            search_reddit(args.search, subreddit=args.sub)
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
