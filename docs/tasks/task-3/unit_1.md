# Unit 1-4: CLI 骨格（scrape コマンド）

## 概要
M1 の各コンポーネントを繋ぎ、`python main.py scrape` として一気通貫で動く CLI を実装する。
Unit 1-2 と Unit 1-3 の両方が完了してから着手する。

---

## ブランチ・PR

```bash
git checkout -b feature/m1-cli-scrape
# 実装後
gh pr create --title "feat: scrape コマンド CLI 骨格（M1 統合）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/main.py` | 新規 |

---

## 実装内容

```python
# src/main.py
@app.command()
def scrape(
    artist: str | None = typer.Option(None, "--artist"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    config = load_config()
    targets = [a for a in config.artists if not artist or a.name == artist]

    for artist_config in targets:
        events = GenericScraper().scrape(artist_config)

        if dry_run:
            print_events(events)
            continue

        created, updated = NotionClient().upsert_events(events)
        # Discord 通知は M2-P5 で追加予定（この時点では TODO コメントのみ）
        log_summary(artist_config.name, created, updated)
```

---

## 統合後のインターフェース

```bash
# 全アーティスト
python main.py scrape

# 特定アーティスト
python main.py scrape --artist avam-fc

# Notion 書き込みなし（確認用）
python main.py scrape --dry-run
```

---

## 人間の介入が必要な手順

- Unit 1-2 の Notion セットアップ（Integration 作成・DB 作成・`.env` 設定）が完了していること
- `config/artists.yaml` に有効なアーティスト設定が1件以上あること

---

## 依存タスク

- Unit 1-2（Notion Client）
- Unit 1-3（HTML スクレイパー）

## 並列実装可能なタスク

なし（M1 の最終統合タスク）
完了後、Unit 2-1 と Unit 2-5 が並列着手可能になる

---

## 完了条件

- [ ] `python main.py scrape --dry-run` でイベント一覧がターミナルに出力される
- [ ] `python main.py scrape` で Notion DB にレコードが作成される
- [ ] `--artist NAME` で特定アーティストのみ処理される
- [ ] 実行後に「新規 N 件 / 更新 N 件 / スキップ N 件」のサマリが出力される

---

## レビュー観点

- `--dry-run` 時に Notion API が一切呼ばれていないか
- アーティストループ中の1件失敗が他のアーティストの処理を止めないか
- Discord 通知の呼び出し箇所が TODO コメントで明示されているか（M2-P5 接続口）
- ログ出力が構造化されていて定期実行ログとして読みやすいか
