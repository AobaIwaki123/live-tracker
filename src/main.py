"""CLI エントリーポイント — analyze / scrape / enrich サブコマンドを提供する。(参照: docs/implementation-plan.md § M1-P4)"""
from __future__ import annotations

import logging
import sys
from typing import Optional

import typer

from src.analyzer.config_writer import write_site_config
from src.analyzer.site_analyzer import analyze_site, capture_page
from src.config import ArtistConfig, _PROJECT_ROOT, load_config
from src.enricher.enricher import Enricher
from src.models.event import LiveEvent
from src.notion.client import NotionClient
from src.notifier.discord import DiscordNotifier
from src.notifier.weekly_summary import WeeklySummaryNotifier
from src.scrapers.generic import GenericScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer(add_completion=False)


def _print_events(events: list[LiveEvent]) -> None:
    if not events:
        typer.echo("  (イベントなし)")
        return
    for e in events:
        typer.echo(f"  [{e.date}] {e.title} @ {e.venue or '会場未定'} ({e.fetch_status})")


def _log_summary(
    artist_name: str,
    created: list[LiveEvent],
    updated: list[tuple[LiveEvent, dict]],
    total: int,
) -> None:
    skipped = total - len(created) - len(updated)
    typer.echo(
        f"[{artist_name}] 新規 {len(created)} 件 / 更新 {len(updated)} 件 / スキップ {skipped} 件"
    )


@app.command()
def analyze(
    artist: str | None = typer.Option(None, "--artist", help="特定アーティストのみ解析"),
    force: bool = typer.Option(False, "--force", help="解析済みでも再解析する"),
) -> None:
    """AI でサイト構造を解析し、config/artists.yaml を更新する。"""
    config = load_config()
    targets: list[ArtistConfig] = [
        a for a in config.artists if not artist or a.name == artist
    ]

    if not targets:
        typer.echo(f"対象アーティストが見つかりません: {artist}", err=True)
        raise typer.Exit(code=1)

    yaml_path = _PROJECT_ROOT / "config" / "artists.yaml"

    for artist_config in targets:
        if artist_config.analyzed_at and not force:
            typer.echo(
                f"{artist_config.name}: 解析済み（{artist_config.analyzed_at}）。--force で再解析可"
            )
            continue
        try:
            typer.echo(f"{artist_config.name}: ページをキャプチャ中...")
            html, logs = capture_page(artist_config.base_url)
            typer.echo(f"{artist_config.name}: AI でサイト構造を解析中...")
            site_config = analyze_site(artist_config.base_url, html, logs)
            if site_config is None:
                typer.echo(f"[{artist_config.name}] 解析に失敗しました。スキップします", err=True)
                continue
            write_site_config(yaml_path, artist_config.name, site_config)
            typer.echo(f"完了: config/artists.yaml を確認してください（{artist_config.name}）")
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] 解析中にエラーが発生しました: %s", artist_config.name, exc)


@app.command()
def scrape(
    artist: Optional[str] = typer.Option(None, "--artist", help="特定アーティストのみ処理"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Notion への書き込みを行わず確認のみ"),
) -> None:
    """スケジュールをスクレイピングして Notion DB へアップサートする。"""
    config = load_config()
    targets: list[ArtistConfig] = [
        a for a in config.artists if not artist or a.name == artist
    ]

    if not targets:
        typer.echo(f"対象アーティストが見つかりません: {artist}", err=True)
        raise typer.Exit(code=1)

    for artist_config in targets:
        try:
            logger.info("スクレイピング開始: %s (%s)", artist_config.name, artist_config.base_url)
            events = GenericScraper().scrape(artist_config)
            logger.info("取得イベント数: %d", len(events))

            if dry_run:
                typer.echo(f"\n--- {artist_config.name} ({len(events)} 件) ---")
                _print_events(events)
                continue

            if config.env.notion_token and config.env.notion_database_id:
                created, updated = NotionClient().upsert_events(events)
            else:
                logger.warning("NOTION_TOKEN / NOTION_DATABASE_ID 未設定のため Notion 書き込みをスキップします")
                created, updated = [], []

            notifier = DiscordNotifier(webhook_url=config.env.discord_webhook_url)
            notifier.notify_batch(created=created, updated=updated)
            _log_summary(artist_config.name, created, updated, len(events))

        except NotImplementedError as exc:
            typer.echo(f"[{artist_config.name}] 未対応の navigation タイプ: {exc}", err=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] 処理中にエラーが発生しました: %s", artist_config.name, exc)


@app.command()
def enrich(
    artist: str | None = typer.Option(None, "--artist", help="特定アーティストのみ処理"),
) -> None:
    """欠損フィールドを AI で補完する（opt-in）。"""
    enricher = Enricher()
    enricher.run(artist_filter=artist)


@app.command()
def summary() -> None:
    """直近 14 日以内のライブ予定を Discord にサマリー送信する。"""
    from src.store.local_store import LocalStore
    store = LocalStore()
    events = store.get_upcoming(days=14)
    if not events:
        typer.echo("直近 14 日以内の予定はありません")
        return
    config = load_config()
    notifier = WeeklySummaryNotifier(webhook_url=config.env.discord_webhook_url or "")
    notifier.send(events)
    typer.echo(f"サマリーを送信しました（{len(events)} 件）")


if __name__ == "__main__":
    app()
