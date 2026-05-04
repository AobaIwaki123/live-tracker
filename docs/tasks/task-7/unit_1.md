# Unit M3-CD: YAML 自動書き戻し + analyze コマンド CLI 統合

## 概要
AI 解析結果を `artists.yaml` に書き戻す `config_writer` と、一連のフローを CLI から呼び出す `analyze` コマンドをまとめて実装する。
設定ライターは analyze コマンドからしか呼ばれないため 1 ユニットとして実装する。

---

## ブランチ・PR

```bash
git checkout -b feature/m3-analyze-command
# 実装後
gh pr create --title "feat: YAML 書き戻し + analyze コマンド（M3 analyze フロー完成）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/analyzer/config_writer.py` | 新規 |
| `src/main.py` | 更新（`analyze` サブコマンド追加） |

---

## 実装内容

### YAML 書き戻し（config_writer.py）

```python
def write_site_config(
    yaml_path: str,
    artist_name: str,
    site_config: SiteConfig,
) -> None:
    """
    artists.yaml の該当アーティストに解析結果をマージして書き戻す。
    name / base_url は保持。analyzed_at を今日の日付に更新。
    """
```

**マージルール:**
- `name` / `base_url` → 保持（上書き禁止）
- `analyzed_at` → 今日の日付（`YYYY-MM-DD`）で更新
- `fetch` / `navigation` / `response` / `selectors` / `detail` → 解析結果で上書き

### analyze コマンド（main.py）

```python
@app.command()
def analyze(
    artist: str | None = typer.Option(None, "--artist"),
    force: bool = typer.Option(False, "--force"),
):
    for artist_config in targets:
        if artist_config.analyzed_at and not force:
            print(f"{artist_config.name}: 解析済み。--force で再解析可")
            continue
        html, logs = capture_page(artist_config.base_url)
        site_config = analyze_site(artist_config.base_url, html, logs)
        write_site_config("config/artists.yaml", artist_config.name, site_config)
        print(f"完了: config/artists.yaml を確認してください")
```

---

## 統合後のインターフェース

```bash
python main.py analyze                        # 未解析アーティスト全件
python main.py analyze --artist avam-fc       # 特定アーティスト
python main.py analyze --artist avam-fc --force  # 強制再解析
```

---

## 人間の介入が必要な手順

1. `python main.py analyze --artist X` 実行後に `config/artists.yaml` を開いてレビューする
2. `selectors` が実際のサイト HTML と一致するか確認する
3. 問題があれば手動修正してから `scrape` コマンドを実行する

---

## 依存タスク

- task-6/unit_2（M3-AB: ネットワークキャプチャ + AI サイト解析）

## 並列実装可能なタスク

なし（M3 最終タスク）

---

## 完了条件

- [ ] `python main.py analyze --artist avam-fc` で `artists.yaml` が正しく更新される
- [ ] `analyzed_at` がある場合、`--force` なしで再解析されない
- [ ] 書き戻し後の YAML が valid として再読み込みできる
- [ ] `name` / `base_url` が書き戻し後も保持されている
- [ ] 複数アーティスト一括解析で 1 件失敗しても他が継続される

---

## レビュー観点

- YAML 書き込み中の例外でファイルが破損しないか（書き込み前にバックアップを取るか）
- `--force` なしで既存設定を上書きしないか
- 解析後に「config/artists.yaml をレビューしてください」メッセージが出るか
- PyYAML の `dump()` でコメントが消えることが仕様として明記されているか
