# Unit M2-P8: WeeklySummaryNotifier + summary コマンド

## 概要

`LocalStore` から直近 2 週間のイベントを取得し、`docs/discord-summary-format.md` のフォーマットで
Discord に週次サマリーを送信する。`python main.py summary` コマンドから呼ばれ、cron でも実行する。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-weekly-summary
gh pr create --title "feat: WeeklySummaryNotifier + summary コマンド（M2-P8）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/notifier/weekly_summary.py` | 新規 |
| `src/main.py` | 更新（`summary` サブコマンド追加） |

---

## 実装内容

### WeeklySummaryNotifier

```python
class WeeklySummaryNotifier:
    def __init__(self, webhook_url: str) -> None: ...

    def send(self, events: list[LiveEvent]) -> None:
        """
        events を日付・週でグルーピングしてフォーマットし Discord へ送信する。
        2000 文字を超える場合は週単位で分割して複数回送信する。
        """

    def _group_by_week(
        self, events: list[LiveEvent]
    ) -> dict[int, list[LiveEvent]]:
        """イベントを週番号（ISO week）でグループ化する。"""

    def _format_week_block(
        self, week_label: str, events: list[LiveEvent]
    ) -> str:
        """1 週分のテキストブロックを生成する。フォーマットは discord-summary-format.md 参照。"""

    def _format_event(self, event: LiveEvent) -> str:
        """1 イベント分の行を生成する。"""
```

### フォーマット仕様

`docs/discord-summary-format.md` を参照。以下のルールを実装する：

| 要素 | 実装ルール |
|---|---|
| 週ヘッダー | `▍ Week N  M/D (曜) 〜 M/D (曜)\n━━━...` |
| 日付ブロック | `📅 YYYY/MM/DD (曜)\n─────...` |
| 同日複数ライブ | `🎤` で区切り、日付ヘッダーは共有 |
| OPEN/START | START のみ判明時は `🕐 START HH:MM` |
| 共演者 | `other_artists` が空でない場合のみ `👥` 行を出力 |
| チケット未確定 | `ticket_url` が空の場合 `🎫 チケット情報未確定` |
| Week N の N | 送信日から見た相対週番号（今週 = 1、来週 = 2） |

### summary コマンド（main.py）

```python
@app.command()
def summary() -> None:
    store = LocalStore()
    events = store.get_upcoming(days=14)
    if not events:
        print("直近 14 日以内の予定はありません")
        return
    notifier = WeeklySummaryNotifier(webhook_url=settings.discord_webhook_url)
    notifier.send(events)
    print(f"サマリーを送信しました（{len(events)} 件）")
```

---

## cron 設定

```cron
# 週次サマリー: 毎週月曜 09:00 JST（= UTC 月曜 00:00）
0 0 * * 1 cd /path/to/idol-live-tracker && uv run python src/main.py summary >> logs/summary-$(date +\%Y-\%m-\%d).log 2>&1
```

---

## 依存タスク

- task-8/unit_1（M2-P7: LocalStore）
- task-4/unit_1（M2-P5: Discord Notifier）— Webhook POST の共通処理を参照

## 並列実装可能なタスク

なし（LocalStore 完了後に実装）

---

## 完了条件

- [ ] `python main.py summary` で Discord にサマリーが届く
- [ ] 同日複数ライブが日付ヘッダーを共有して表示される
- [ ] 週ごとに `▍ Week N` ヘッダーで区切られる
- [ ] イベントが 0 件の場合、Discord に何も送信されない
- [ ] 2000 文字を超えるサマリーが週単位で分割して送信される
- [ ] `DISCORD_WEBHOOK_URL` 未設定時にスキップしログに警告が出る
- [ ] `start_time` が空の場合に `OPEN HH:MM /` が表示されない
- [ ] `other_artists` が空の場合に `👥` 行が表示されない

---

## レビュー観点

- `Week N` の週番号が送信日を基準に正しく計算されているか
- Discord の 2000 文字制限を超えた場合に途中で切れないか（週単位で分割）
- URL を `<URL>` で囲んでプレビュー展開を抑制するか（任意、`discord-summary-format.md` の実装メモ参照）
- 週をまたぐイベントリストで週番号が正しく割り当てられるか
