# Unit 2-5: Discord Notifier

## 概要
スクレイプ後に新規イベントと情報更新を Discord Webhook で通知する。
Unit 1-4 完了後に Unit 2-1 と並列着手可能。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-discord-notifier
# 実装後
gh pr create --title "feat: Discord Webhook 通知（新規・更新の2種類）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/notifier/__init__.py` | 新規 |
| `src/notifier/discord.py` | 新規 |
| `src/main.py` | 更新（TODO コメントを実装に置き換え） |
| `.env.example` | 更新（`DISCORD_WEBHOOK_URL` 追加） |

---

## 実装内容

```python
class DiscordNotifier:
    def __init__(self, webhook_url: str | None):
        self.webhook_url = webhook_url  # None の場合は全メソッドで早期 return

    def notify_created(self, event: LiveEvent) -> None:
        """🆕 新着通知"""

    def notify_updated(self, event: LiveEvent, diff: dict[str, Any]) -> None:
        """🔄 更新通知（diff にどのフィールドが変わったか含める）"""

    def notify_batch(
        self,
        created: list[LiveEvent],
        updated: list[tuple[LiveEvent, dict]],
    ) -> None:
        """連続通知。0.5 秒間隔で送信"""
```

**通知フォーマット（新規）**
```
🆕 新着ライブ情報

🎤 グループ名
📅 2026-08-01  18:00
🏟️ 会場名（都道府県）
🎫 チケット URL

[Notion で見る](https://notion.so/...)
```

**通知フォーマット（更新）**
```
🔄 ライブ情報が更新されました

🎤 グループ名  |  イベントタイトル
📅 2026-08-01
✅ 更新された情報: 会場名, チケット URL

[Notion で見る](https://notion.so/...)
```

---

## 統合後のインターフェース

```python
from src.notifier.discord import DiscordNotifier

notifier = DiscordNotifier(webhook_url=os.getenv("DISCORD_WEBHOOK_URL"))
notifier.notify_batch(created=created_events, updated=updated_events)
```

`main.py` の TODO コメント箇所をこの呼び出しで置き換える。

---

## 人間の介入が必要な手順

1. Discord サーバーの「サーバー設定 → 連携サービス → ウェブフック」で Webhook を作成
2. Webhook URL を `.env` の `DISCORD_WEBHOOK_URL` に設定

---

## 依存タスク

- Unit 1-4（CLI 骨格・scrape コマンド）

## 並列実装可能なタスク

- Unit 2-1（URLGenerator）と並列着手可能

---

## 完了条件

- [ ] 新規イベント作成時に `🆕` 通知が届く
- [ ] フィールド更新時に `🔄` 通知と更新フィールド名が届く
- [ ] 変化なしのとき通知が届かない
- [ ] `DISCORD_WEBHOOK_URL` 未設定でも scrape が正常終了し、警告ログが出る
- [ ] 連続通知で Discord のレート制限エラーが発生しない（0.5 秒間隔）

---

## レビュー観点

- `DISCORD_WEBHOOK_URL` が未設定の場合に scrape コマンド全体がエラーにならないか
- Notion ページ URL が通知に含まれているか（`upsert_events` から `page_id` を受け取れているか）
- Embed の文字数が Discord の上限（4096 文字）を超えないか
