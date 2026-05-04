# Unit 2-6: 定期実行セットアップ

## 概要
cron を使った定期実行の設定手順と、ログ保存の仕組みを整える。
コードの追加はほぼなく、ドキュメントとディレクトリ整備が主体。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-cron-setup
# 実装後
gh pr create --title "docs: cron 定期実行セットアップ手順" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `logs/.gitkeep` | 新規 |
| `.gitignore` | 更新（`logs/*.log` を除外） |
| `README.md` | 更新（定期実行セクション追加） |

---

## 実装内容

### README に追記する内容

```markdown
## 定期実行（cron）

### 設定手順

1. ターミナルで `crontab -e` を開く
2. 以下を追加して保存（毎朝9時に実行する例）：

cron
0 9 * * * cd /絶対パス/idol-live-tracker && /usr/bin/python3 src/main.py scrape >> logs/$(date +\%Y-\%m-\%d).log 2>&1


3. `crontab -l` で設定を確認する

### ログの確認

logs/YYYY-MM-DD.log に日付ごとのログが保存されます。
古いログは手動で削除してください（月1回程度推奨）。
```

---

## 統合後のインターフェース

```bash
# 設定確認
crontab -l

# ログ確認
tail -f logs/$(date +%Y-%m-%d).log
```

---

## 人間の介入が必要な手順

1. `crontab -e` でスケジュールを設定する（README 参照）
2. Python の絶対パスを `which python3` で確認して cron に記載する
3. 初回実行後に `logs/` にファイルが作成されることを確認する

---

## 依存タスク

- Unit 2-5（Discord Notifier）

## 並列実装可能なタスク

なし（M2 の最終タスク）

---

## 完了条件

- [ ] `logs/` ディレクトリと `.gitkeep` が作成されている
- [ ] `.gitignore` に `logs/*.log` が追加されている
- [ ] README にコピペで使える cron 設定例が記載されている

---

## レビュー観点

- cron の実行パスに Python の仮想環境が含まれているか（venv を使う場合は要注意）
- ログファイルのパスが cron 実行時の作業ディレクトリに依存しないか（絶対パス推奨）
