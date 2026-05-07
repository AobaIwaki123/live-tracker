# analyze コマンド — マルチターン自己修正ループ設計書

## 概要

`analyze` コマンドは AI に Web サイト構造を解析させ、スクレイパー設定（YAML）を自動生成する。
当初は 1 ショット呼び出しだったが、以下の 3 フェーズのループに発展した。

```
Phase 1: HTML + イベント要素スニペット → 初期設定生成
Phase 2: 完全性チェック → 不足フィールドを同一セッションで補完
Phase 3: 実スクレイプ検証 → 0 件なら実ページ HTML をフィードバックして再修正
```

各フェーズは同一のチャットセッションで継続されるため、AI は前のターンの文脈を保持したまま修正を行う。

---

## 背景と課題

### 1 ショット呼び出しの限界

当初の `analyze_site()` は 1 回の AI 呼び出しで設定を生成していた。
この方式では以下の問題が頻発した：

| 問題 | 原因 |
|---|---|
| セレクタが存在しないクラス名を生成（ハルシネーション） | AI がランディングページの HTML を見ずに「よくある設定」を推測していた |
| `date_format` が欠落 | スキーマ説明に必須として明示されていなかった |
| `pattern` が相対パスのまま | `{base_url_origin}` プレースホルダーへの依存 |
| 設定が完全でも実際に 0 件取得 | DOM 要素の存在とパース成功は別問題 |

---

## 工夫点 1: フル HTML からのスニペット抽出

### 問題

`capture_page()` はページ HTML を取得するが、スケジュール要素はページ後半に埋まっていることが多い。
例: DeNA ベイスターズのスケジュール要素は HTML の **102,672 文字目**に出現するが、AI に渡す HTML は先頭 20,000 字に制限している。
このため AI はスケジュール要素を見ることができず、ハルシネーションが発生する。

### 解決策

`capture_page()` をフル HTML を返す仕様に変更し、`_build_prompt()` 内で以下の 2 段階処理を行う：

1. フル HTML から `_extract_event_snippets()` でスケジュール関連要素を抽出
2. AI 本文には先頭 20,000 字の HTML を渡しつつ、スニペットを別セクションとして追加

```python
snippets_text = _extract_event_snippets(html)   # フル HTML から抽出
html_for_prompt = html[:20000]                   # AI 本文は 20,000 字に制限
```

### スニペット抽出ロジック (`_extract_event_snippets`)

BeautifulSoup でクラス名に `schedule|event|live|match|game|calendar|concert|ticket` を含む要素を全件スキャンする。
そのうえで **出現回数が多い順にソート** して上位 5 タイプを返す。

```python
sorted_groups = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
```

**なぜ出現回数順か：** リストアイテム（イベント要素）は繰り返し出現するが、コンテナ要素（`body`・`section` 等）は 1 件しか出現しない。この性質を使ってリストアイテムを優先して取り出す。

また、`outerHTML` が 3,000 字を超える要素はコンテナと判断して除外する。

```
DeNA の場合:
  26件  td.calendar--hasmatch  ← 優先取得される
  11件  div.event_icon
   8件  a.button.button--ticket
   ...
  1件   body.game-schedule      ← 除外（大型コンテナ）
```

---

## 工夫点 2: マルチターン ChatSession の抽象化

### 設計

`AIProvider` に `chat_session(system) -> ChatSession` を追加した。
`ChatSession.send(user) -> str` を繰り返し呼ぶことで会話履歴が蓄積される。

```
AIProvider (ABC)
├── ClaudeProvider
│   └── _ClaudeChatSession  — messages: list[dict] を持ち回り
└── GeminiProvider
    └── _GeminiChatSession  — client.chats.create() でネイティブセッション管理
```

### Claude と Gemini の差異

| 項目 | Claude | Gemini |
|---|---|---|
| 会話履歴の持ち方 | `messages=[{role, content}, ...]` を毎回送信 | `client.chats.create()` がサーバー側でセッション管理 |
| システムプロンプト | API パラメータとして別送 | `GenerateContentConfig(system_instruction=...)` で設定 |

### 既存コードへの影響

`complete(system, user)` は変更なし。`chat_session()` は新規追加のみなので、`enrich` や他のコマンドには影響しない。

---

## 工夫点 3: 3 フェーズの自己修正ループ

```
analyze_site()
    │
    ├─ Phase 1 (Turn 1)
    │    HTML + ネットワークログ + スニペット → 初期 SiteConfig
    │
    ├─ Phase 2 (Turn 2〜3, 最大 _MAX_FOLLOWUP_TURNS=2 回)
    │    _check_completeness() で必須フィールドを検査
    │    不足があれば「X が不足しています」と伝えて補完を要求
    │    完全になった時点でフェーズ終了
    │
    └─ Phase 3 (最大 _MAX_VALIDATION_TURNS=2 回)
         _validate_config() で実際の URL をフェッチ
         event_list セレクタが 0 件 → 実ページ HTML スニペットを渡して再修正
         0 件でなければ完了
```

最大ターン数: 1 + 2 + 2 = **5 ターン**

### Phase 2: 完全性チェック (`_check_completeness`)

Navigation タイプごとに必須フィールドを定義し、欠けているフィールドパスのリストを返す。

```python
# path_segment / query_param / single_page / pagination_links の場合
if "date_format" not in config.selectors:
    missing.append("selectors.date_format")
```

**`date_format` を必須にした理由：**
`p.day` のような日付セレクタは `"1"` という数値のみ返す。
スクレイパー側でこれを日付として解釈するには `date_format: '%d'` が必要。
これがないと全イベントの日付パースが失敗し、スクレイプ結果が 0 件になる。
（実際に起きた障害: バリデーションが 26 件成功を報告したにもかかわらず本番スクレイプが 0 件）

### Phase 3: バリデーション (`_validate_config`)

完全性チェックは「フィールドが存在するか」しか見ない。
セレクタが実際の HTML にマッチするかは確認できないため、実スクレイプ検証を追加した。

```python
page = Fetcher().get(url, timeout=30)
elements = page.css(event_list_selector)
count = len(elements)
```

0 件のとき、フォローアップターンで **バリデーション URL のページから抽出したスニペット** を AI に渡す。
これはランディングページのスニペットとは異なる場合がある（例: 年次ページ vs 月次ページ）。

```
バリデーション URL: https://www.baystars.co.jp/game/schedule/2026/05
ランディング URL:   https://www.baystars.co.jp/game/schedule/2026
```

---

## 工夫点 4: システム側での相対パス正規化

### 問題

AI が生成する `navigation.pattern` は以下の 3 形式が混在する：

```
/game/schedule/{year}/{month:02d}         ← 相対パス（AI が生成しやすい）
{base_url_origin}/game/schedule/...       ← プレースホルダー使用
https://www.baystars.co.jp/game/...       ← 絶対 URL
```

これを AI プロンプトで強制するのはコスト（Few-shot 例・検証ループ）が高い。

### 解決策

`url_generator.py` の `path_segment` ケースでフォールバック処理を追加した。
`api_endpoint` の既存実装と統一した形。

```python
if not url.startswith("http://") and not url.startswith("https://"):
    url = f"{config.base_url_origin}{url}"
```

AI は「相対パスでも絶対パスでも書けばよい」状態になり、プロンプトへの依存が減る。

---

## 設定スキーマへの追加

HTML スクレイピング型の `selectors` に `date_format` を必須フィールドとして追加した：

```yaml
selectors:
  event_list: td.calendar--hasmatch
  title: p.name span:last-child
  date: p.day
  date_format: '%d'        # ← 追加。YYYY-MM-DD 等の標準フォーマットなら ""
  venue: p.location::regex(...)
```

`date_format` が `""` の場合は `_parse_date()` がデフォルトフォーマット群（`%Y年%m月%d日` / `%Y/%m/%d` / `%Y-%m-%d`）でフォールバック解析する。

---

## `_merge_configs` の設計判断

フォローアップターンで AI が返した設定を元の設定にマージする際、`None` のみを「未設定」として扱い `""` や `False`・`0` は有効値として保持する：

```python
if v is not None:
    merged[k] = v
```

**理由：** `date_format: ""` は「空文字（デフォルトフォールバックを使う）」という有効な指示だが、falsy 判定（`if v`）では上書きをスキップしてしまう。

---

## ターン数とコストのトレードオフ

| フェーズ | 最大追加ターン | 典型的な使用 |
|---|---|---|
| Phase 1（初期生成） | 0（必ず 1 回） | 常に実行 |
| Phase 2（完全性） | 2 | 0〜1 回が多い |
| Phase 3（検証） | 2 | 0〜1 回が多い |

実際の DeNA ベイスターズの例: Phase 1 のみで完全性 OK、Phase 3 の 1 回目で 26 件を確認して終了（合計 2 API コール）。

Phase 3 のバリデーションフェッチは API コールではなく HTTP リクエストのため、コストは発生しない。

---

## 関連ファイル

| ファイル | 変更内容 |
|---|---|
| `src/ai/provider.py` | `ChatSession` ABC + `_ClaudeChatSession` / `_GeminiChatSession` 追加、`AIProvider.chat_session()` 追加 |
| `src/analyzer/site_analyzer.py` | `capture_page()` フル HTML 返却、`_extract_event_snippets()` 追加、`analyze_site()` を 3 フェーズループに変更、`_validate_config()` / `_build_validation_url()` / `_build_validation_feedback()` 追加、`_check_completeness()` に `date_format` 追加 |
| `src/scrapers/url_generator.py` | `path_segment` ケースに相対パス → 絶対 URL 正規化を追加 |
