"""CLI エントリーポイント — analyze / scrape / enrich サブコマンドを提供する。(参照: docs/implementation-plan.md § M1-P4)"""
from __future__ import annotations

import logging
import sys
from typing import Optional

import typer

from src.config import ArtistConfig, load_config
from src.models.event import LiveEvent
from src.notion.client import NotionClient
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

            created, updated = NotionClient().upsert_events(events)
            # TODO: Discord 通知 (M2-P5 で実装予定)
            _log_summary(artist_config.name, created, updated, len(events))

        except NotImplementedError as exc:
            typer.echo(f"[{artist_config.name}] 未対応の navigation タイプ: {exc}", err=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] 処理中にエラーが発生しました: %s", artist_config.name, exc)


if __name__ == "__main__":
    app()
