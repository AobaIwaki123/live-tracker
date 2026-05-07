"""Discord Webhook 通知モジュール — 新規・更新イベントを Embed 形式で送信する。(参照: docs/requirements.md § FR-04)"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.models.event import LiveEvent

logger = logging.getLogger(__name__)

_MAX_EMBED_LENGTH = 4096


class DiscordNotifier:
    """Discord Webhook を使って新規・更新イベントを通知するクラス。

    ``webhook_url`` が None または空文字の場合、全メソッドで送信をスキップして
    警告ログを一度だけ出力する（FR-04-6）。

    Attributes:
        webhook_url: Discord Webhook URL。None または空文字でスキップ。
    """

    def __init__(self, webhook_url: str | None) -> None:
        self.webhook_url = webhook_url or ""
        self._warned = False

    def _skip_with_warning(self) -> bool:
        """送信をスキップすべきか判定し、必要なら警告ログを出力する。

        Returns:
            True のとき呼び出し元は早期 return すべき。
        """
        if not self.webhook_url:
            if not self._warned:
                logger.warning(
                    "DISCORD_WEBHOOK_URL が未設定のため Discord 通知をスキップします。"
                    " .env に DISCORD_WEBHOOK_URL を設定してください。"
                )
                self._warned = True
            return True
        return False

    def _send(self, description: str) -> None:
        """Discord Webhook に Embed payload を POST する。

        Embed の description が 4096 文字を超える場合は末尾を切り捨てる。
        HTTP エラー時はログ警告を出してスキップし、例外を送出しない。

        Args:
            description: Embed の description 文字列。
        """
        if len(description) > _MAX_EMBED_LENGTH:
            description = description[:_MAX_EMBED_LENGTH]

        payload: dict[str, Any] = {"embeds": [{"description": description}]}
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Discord 通知の送信に失敗しました: %s", exc)

    def notify_created(self, event: LiveEvent) -> None:
        """新着ライブイベントを Discord に通知する（FR-04-2 ①）。

        通知フォーマット:
        ```
        🆕 新着ライブ情報

        🎤 グループ名
        📅 開催日  開始時刻
        🏟️ 会場名（都道府県）
        🎫 チケット URL

        <source_url>
        ```

        Args:
            event: 新規作成されたライブイベント。
        """
        if self._skip_with_warning():
            return

        lines: list[str] = ["🆕 新着ライブ情報", ""]
        lines.append(f"🎤 {event.artist}")

        date_str = str(event.date) if event.date else "日付未定"
        time_str = f"  {event.start_time}" if event.start_time else ""
        lines.append(f"📅 {date_str}{time_str}")

        if event.venue or event.prefecture:
            venue_str = event.venue or ""
            pref_str = f"（{event.prefecture}）" if event.prefecture else ""
            lines.append(f"🏟️ {venue_str}{pref_str}")

        if event.ticket_url:
            lines.append(f"🎫 {event.ticket_url}")

        lines.append("")
        if event.source_url:
            lines.append(f"<{event.source_url}>")

        self._send("\n".join(lines))

    def notify_updated(self, event: LiveEvent, diff: dict[str, Any]) -> None:
        """ライブイベントの情報更新を Discord に通知する（FR-04-2 ②）。

        通知フォーマット:
        ```
        🔄 ライブ情報が更新されました

        🎤 グループ名  |  イベントタイトル
        📅 開催日
        ✅ 更新された情報: フィールド名1, フィールド名2

        <source_url>
        ```

        diff に含まれるフィールド名はユーザー可読な日本語ラベルに変換して表示する。

        Args:
            event: 更新されたライブイベント。
            diff: ``{field_name: new_value}`` の差分辞書（LocalStore.upsert_many_diff の戻り値）。
        """
        if self._skip_with_warning():
            return

        lines: list[str] = ["🔄 ライブ情報が更新されました", ""]
        lines.append(f"🎤 {event.artist}  |  {event.title}")

        date_str = str(event.date) if event.date else "日付未定"
        lines.append(f"📅 {date_str}")

        field_labels: dict[str, str] = {
            "title":         "イベントタイトル",
            "artist":        "グループ名",
            "date":          "開催日",
            "start_time":    "開始時刻",
            "venue":         "会場名",
            "prefecture":    "都道府県",
            "ticket_url":    "チケット URL",
            "ticket_price":  "チケット料金",
            "other_artists": "出演アーティスト",
            "poster_url":    "ポスター画像 URL",
            "source_url":    "ソース URL",
            "fetch_status":  "取得ステータス",
        }
        updated_entries = [
            f"{field_labels.get(k, k)}: {v}"
            for k, v in diff.items()
            if k != "fetch_status"
        ]
        if updated_entries:
            lines.append("✅ 更新された情報:")
            lines.extend(f"　• {entry}" for entry in updated_entries)

        lines.append("")
        if event.source_url:
            lines.append(f"<{event.source_url}>")

        self._send("\n".join(lines))

    def notify_batch(
        self,
        created: list[LiveEvent],
        updated: list[tuple[LiveEvent, dict]],
    ) -> None:
        """複数の新規・更新通知を 0.5 秒間隔で連続送信する（FR-04-2）。

        created と updated が共に空の場合は何もしない。

        Args:
            created: 新規作成されたライブイベントのリスト。
            updated: ``[(event, diff), ...]`` の更新イベントリスト。
        """
        if not created and not updated:
            return

        all_calls: list[tuple] = []
        for event in created:
            all_calls.append(("created", event, {}))
        for event, diff in updated:
            all_calls.append(("updated", event, diff))

        for i, (kind, event, diff) in enumerate(all_calls):
            if i > 0:
                time.sleep(0.5)
            if kind == "created":
                self.notify_created(event)
            else:
                self.notify_updated(event, diff)
