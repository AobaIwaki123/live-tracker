# Unit 3-6: enrich コマンド CLI 統合

## 概要
Unit 3-5 を `python main.py enrich` として呼び出せる CLI を実装する。
このタスク完了で全機能が揃い、完成形になる。

---

## ブランチ・PR

```bash
git checkout -b feature/m3-cli-enrich
# 実装後
gh pr create --title "feat: enrich コマンド CLI 統合（M3 完成）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/main.py` | 更新（`enrich` サブコマンド追加） |

---

## 実装内容

```python
@app.command()
def enrich(
    artist: str | None = typer.Option(None, "--artist"),
):
    notion = NotionClient()
    enricher = Enricher()

    all_records = notion.fetch_all()
    targets = [
        e for e in all_records.values()
        if e.fetch_status != "完全取得"
        and (not artist or e.artist == artist)
    ]

    print(f"補完対象: {len(targets)} 件")
    updated = enricher.enrich_all(targets)
    print(f"補完完了: {len(updated)} 件 / スキップ: {len(targets) - len(updated)} 件")
```

---

## 統合後のインターフェース

```bash
# 全アーティストの未取得レコードを補完
python main.py enrich

# 特定アーティストのみ
python main.py enrich --artist avam-fc
```

---

## 人間の介入が必要な手順

なし

---

## 依存タスク

- task-3/unit_2（M3-P5: AI エンリッチメント）
- task-3/unit_1（M1-P4: CLI 骨格 — typer アプリに追記するため）

## 並列実装可能なタスク

- task-4/unit_1（M2-P1: URLGenerator）と同時着手可能
- task-4/unit_2（M2-P5: Discord Notifier）と同時着手可能

---

## 完了条件

- [ ] `python main.py enrich` で `一部未取得` レコードの補完が実行される
- [ ] 補完件数・スキップ件数のサマリが出力される
- [ ] `--artist NAME` で特定アーティストのみ絞り込める

---

## レビュー観点

- `完全取得` のレコードが対象外になっているか
- 補完対象が 0 件の場合に適切なメッセージが出るか
- enrich コマンドを複数回実行しても冪等か（同じ結果になるか）
