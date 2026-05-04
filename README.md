# idol-live-tracker

アイドルアーティストのライブスケジュールを公式サイトからスクレイプして Notion に同期する Python CLI ツール。

## セットアップ

### 必要環境

- Python 3.10+
- uv

### インストール

```bash
uv sync
cp .env.example .env  # シークレットを記入
```

### Playwright セットアップ（JS レンダリングが必要なサイト用）

`fetch.dynamic: true` に設定したアーティストは初回のみ以下を実行:

```bash
uv run scrapling install
```

## 使い方

```bash
uv run python src/main.py analyze [--artist NAME] [--force]   # Phase 1: AI がサイトを解析して YAML 設定を生成
uv run python src/main.py scrape  [--artist NAME] [--dry-run]  # Phase 2: スクレイプして SQLite・Notion・Discord に送信
uv run python src/main.py enrich  [--artist NAME]              # Phase 3: AI が不足フィールドを補完（opt-in）
uv run python src/main.py summary                              # 直近 14 日のサマリーを Discord に送信
```

## 定期実行（cron）

### 設定手順

1. ターミナルで `crontab -e` を開く
2. 以下を追加して保存（毎朝9時に実行する例）:

```cron
# scrape: 毎朝9時
0 9 * * * cd /絶対パス/idol-live-tracker && uv run python src/main.py scrape >> logs/$(date +\%Y-\%m-\%d).log 2>&1

# 週次サマリー: 毎週月曜09時（JST = UTC 0時）
0 0 * * 1 cd /絶対パス/idol-live-tracker && uv run python src/main.py summary >> logs/summary-$(date +\%Y-\%m-\%d).log 2>&1
```

3. `crontab -l` で設定を確認する

> **注意**: `/絶対パス/` の部分は実際のプロジェクトパスに置き換えること（`pwd` で確認）。
> `uv run` を使うことで仮想環境が自動的に有効になる。

### ログの確認

```bash
tail -f logs/$(date +%Y-%m-%d).log
```

`logs/YYYY-MM-DD.log` に日付ごとのログが保存される。古いログは月1回程度手動削除を推奨。
