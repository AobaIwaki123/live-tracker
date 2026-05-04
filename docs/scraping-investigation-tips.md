# サイト調査 Tips — 新アーティスト追加時の手順

新しいアーティストの `base_url` を追加するとき、どの navigation タイプ・セレクターを使うかを調べる手順。

---

## Step 1. ブラウザでページを開き、ネットワークを確認する

Playwright MCP でページを開き、XHR/Fetch リクエストを確認する。

```
目的: スケジュール情報を API で取得しているか、HTML に直接書かれているかを判定する
```

確認ポイント:
- `schedule`, `event`, `live`, `api` などのキーワードを含む XHR/Fetch リクエストがあるか
- POST リクエストに日付パラメータが含まれるか（`api_endpoint` タイプの可能性）
- ネットワークリクエストが何もなければ HTML スクレイピング（`single_page` 等）

**API が見つかった場合 → Step 2-A へ**
**API が見つからなかった場合 → Step 2-B へ**

---

## Step 2-A. API タイプの調査

XHR リクエストのエンドポイント・メソッド・ボディ・レスポンスを確認する。

確認ポイント:
- エンドポイントパス（例: `/api/schedule/get`）
- GET か POST か
- POST ボディに月の範囲（`start`, `end` など）が含まれるか
- レスポンスが JSON 配列か、オブジェクトの中に配列があるか
- イベントの各フィールド名（`title`, `date`, `id` など）

YAML に書く内容:
```yaml
navigation:
  type: api_endpoint
  endpoint: /api/schedule/get
  method: POST
  body_template:
    start: '{month_start}'
    end: '{month_end}'
  range_months: 3
response:
  format: json_array          # or json_object_with_array
  array_path: ''              # json_object_with_array の場合はキー名
  mapping:
    id: id
    title: title
    date: reception_date
    date_format: '%Y-%m-%d'
```

---

## Step 2-B. HTML タイプの調査

Playwright の snapshot でページのアクセシビリティツリーを確認し、イベントリストの大まかな構造を把握する。

確認ポイント:
- イベントが `<ul> > <li>` 構造になっているか
- 日付・タイトル・会場がどの要素に入っているか
- 全件が 1 ページにあるか（`single_page`）、ページネーションがあるか

---

## Step 3. scrapling でセレクターを実際に試す

アクセシビリティツリーだけではクラス名が不明なことが多いため、scrapling で HTML を取得して直接確認する。

```python
from scrapling.fetchers import Fetcher
page = Fetcher().get('https://example.com/schedule', timeout=30)

# 1. 候補のセレクターを当たりをつけて試す
items = page.css('li.clearfix')
print(f'件数: {len(items)}')

# 2. 最初の要素の子要素を列挙してクラス名を確認する
if items:
    for el in items[0].css('*')[:30]:
        print(f'<{el.tag} class={el.attrib.get("class","")!r}> {(el.text or "")[:40]!r}')

# 3. フィールドごとに実際に取得できるか確認する
for item in items:
    print(item.css('h4 a')[0].text if item.css('h4 a') else 'NO TITLE')
```

---

## Step 4. セレクターのパターン

`_resolve_field` が対応しているセレクター記法:

| やりたいこと | 書き方 | 例 |
|---|---|---|
| テキストを取得 | セレクタのみ | `div.event h4 a` |
| 属性を取得 | `::attr(属性名)` | `h4 a::attr(href)` |
| テキストから正規表現で抽出 | `セレクタ::regex(パターン)` | `div.date p::regex(\d{4}-\d{2}-\d{2})` |
| 正規表現のグループ1を返す | パターンに `()` を含める | `span.s::regex(開演\s*(\d+:\d+))` |

日付は `%Y-%m-%d`, `%Y/%m/%d`, `%Y年%m月%d日` の3形式をデフォルトでサポート。それ以外は `::regex()` で抽出してから渡す。

---

## Step 5. dry-run で動作確認

```bash
uv run lt scrape --artist <name> --dry-run
```

件数・日付・タイトル・会場が正しく取れているか確認する。0件の場合はセレクターが間違っている。

---

## よくある落とし穴

- **`p.dayN` のクラス名が曜日で変わる**: `p.day0`〜`p.day6` のように曜日番号が入るサイトがある。`div.date p::regex(\d{4}-\d{2}-\d{2})` のように regex で日付を抽出するのが安全。
- **テキストが入れ子要素に分割されている**: `get_all_text()` を使うと子要素のテキストも結合して取れる。scrapling 調査時は `el.text` より `el.get_all_text()` で確認する。
- **静的フェッチで取れない場合**: JS が必要なら `fetch.dynamic: true` に変更して DynamicFetcher（Playwright）を使う。
- **イベントが0件になる**: `event_list` セレクターが合っていないことが多い。scrapling で `len(page.css('セレクター'))` を確認する。
