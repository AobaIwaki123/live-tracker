# Discord 通知 URL フォーマット変更計画

## 目的

Discord でリンクをクリックした際に出る「外部リンクを開きますか？」のポップアップを排除する。  
Markdown リンク記法 `[テキスト](url)` から、直接 URL を貼る形式へ変更する。

---

## 現状の問題

Discord のデスクトップアプリ・モバイルアプリは、Embed の description などで
`[表示テキスト](url)` 形式（masked hyperlink）を使うと、クリック時に外部リンク確認ポップアップを表示する。  
これはセキュリティ上の仕様であり、表示テキストと遷移先 URL が異なるため警告される。

---

## Discord の URL 記法一覧と挙動比較

| 記法 | 例 | クリック時の挙動 | プレビュー展開 |
|------|-----|----------------|--------------|
| Masked hyperlink | `[ソースで見る](url)` | ポップアップあり | なし（embed 内） |
| 角括弧付き裸 URL | `<https://example.com>` | 直接開く | 展開されない（抑制） |
| 裸 URL | `https://example.com` | 直接開く | 展開される（embed ブロックが出る） |

**採用方針: `<url>` 形式**（角括弧付き裸 URL）

- ポップアップなしで直接開く
- プレビュー展開を抑制するため通知が長くならない
- `weekly_summary.py` の `ticket_url` が既に同形式 → 記法を統一できる

---

## 変更対象ファイル

### 1. `src/notifier/discord.py`

#### 変更箇所 A — `notify_created` メソッド

```
# 変更前 (line 104)
lines.append(f"[ソース URL で見る]({event.source_url})")

# 変更後
lines.append(f"<{event.source_url}>")
```

合わせて docstring のフォーマット例（line 78）も更新する:

```
# 変更前
🎫 チケット URL

[ソース URL で見る](source_url)

# 変更後
🎫 チケット URL

<source_url>
```

#### 変更箇所 B — `notify_updated` メソッド

```
# 変更前 (line 161)
lines.append(f"[ソース URL で見る]({event.source_url})")

# 変更後
lines.append(f"<{event.source_url}>")
```

合わせて docstring のフォーマット例（line 118）も更新する。

---

### 2. `src/notifier/weekly_summary.py`

`_format_event` の `ticket_url` は既に `<{event.ticket_url}>` 形式を使用している。  
変更不要。

---

## 変更のスコープと影響範囲

| 項目 | 影響 |
|------|------|
| `notify_created` の出力フォーマット | source_url がある場合のみ表示行が変化 |
| `notify_updated` の出力フォーマット | 同上 |
| `notify_batch` | 内部で上記2メソッドを呼ぶだけ。変更不要 |
| `WeeklySummaryNotifier` | 変更なし |
| テスト / スナップショット | `notify_created` / `notify_updated` の出力文字列に依存するテストがあれば更新が必要 |
| `_send` / `_post` の HTTP ロジック | 変更なし |

---

## 実装手順

1. `src/notifier/discord.py` を開く
2. `notify_created` の `source_url` 行（line 104 付近）を `<{event.source_url}>` に修正
3. 同メソッドの docstring フォーマット例を合わせて修正
4. `notify_updated` の `source_url` 行（line 161 付近）を同様に修正
5. 同メソッドの docstring フォーマット例を合わせて修正
6. 既存テストがあれば期待値文字列を更新

---

## 非対象・考慮しないこと

- `source_url` が `None` の場合の挙動は変わらない（既存の `if event.source_url:` ガードは維持）
- Discord の Embed フィールドやタイトルへの変更はしない
- `ticket_url` の表示方法は変更しない（既に正しい形式）
