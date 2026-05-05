# サイト調査 Tips — 新アーティスト追加時の手順

新しいアーティストの `base_url` を追加するとき、どの navigation タイプ・セレクターを使うかを調べる手順。

---

## Step 1. ブラウザでページを開き、ネットワークを確認する

Playwright MCP やブラウザのデベロッパーツールでページを開き、XHR/Fetch リクエストを確認する。

```
目的: スケジュール情報を API で取得しているか、HTML に直接書かれているかを判定する
```

確認ポイント:
- `schedule`, `event`, `live`, `api` などのキーワードを含む XHR/Fetch リクエストがあるか
- **API が見つかった場合**: `api_endpoint` タイプの可能性が高い（Step 2-A へ）
- **リクエストに特殊なヘッダーが必要か**: `x-timetreea` や `Authorization` などがないとエラーになる場合がある
- **ネットワークリクエストが何もなければ**: HTML スクレイピング（Step 2-B へ）

---

## Step 2-A. API タイプの調査

XHR リクエストのエンドポイント・メソッド・ボディ・レスポンスを確認する。

### 基本の確認ポイント
- **エンドポイント**: 相対パス（`/api/schedule`）か絶対 URL か
- **メソッド**: GET または POST
- **パラメータ/ボディ**: 月の範囲指定があるか
    - 日付形式（`2026-05-01`）か Unix タイムスタンプ（`1777215600000`）か
- **ヘッダー**: 特定のカスタムヘッダーが必要か（例: TimeTree の `x-timetreea`）
- **レスポンス構造**: 配列がどこにあるか（`array_path`）
- **フィールド名**: タイトル・日付・会場・リンクなどがどのキーにあるか、ネストしているか
- **フィールドに複数アーティスト分が混在していないか**（後述）

### YAML 設定例（基本）
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
  format: json_array
  mapping:
    id: id
    title: title
    date: date
    date_format: '%Y-%m-%d'
```

### YAML 設定例（高度な設定）
```yaml
navigation:
  type: api_endpoint
  endpoint: /api/v2/events?from={month_start_ms}&to={month_end_ms}
  method: GET
  headers:
    x-timetreea: web/2.1.0/en  # 必須ヘッダーがある場合
  range_months: 3
response:
  format: json_object_with_array
  array_path: public_events
  mapping:
    id: id
    title: title
    date: start_at
    date_format: ''         # 空なら Unix タイムスタンプとして扱う
    venue: location_name
    start_time: note::regex(開演時刻\s*(\d+:\d+))  # 正規表現抽出も可能
    ticket_url: link_url
    source_url: url
```

### サポートするプレースホルダー
`endpoint` 文字列および `body_template` 内で使用可能：

| プレースホルダー | 展開後の値 |
|---|---|
| `{month_start}` | その月の初日（`YYYY-MM-DD`） |
| `{month_end}` | その月の末日（`YYYY-MM-DD`） |
| `{month_start_ms}` | 初日 0:00:00 の Unix タイムスタンプ（ミリ秒） |
| `{month_end_ms}` | 末日 23:59:59 の Unix タイムスタンプ（ミリ秒） |
| `{year}` | 4桁の西暦年（`2026`） |
| `{month}` | 2桁の月（`05`） |

---

## Step 2-B. HTML タイプの調査

Playwright の snapshot 等でページの構造を確認し、イベントリストのセレクターを特定する。

確認ポイント:
- イベントが `<ul> > <li>` 構造になっているか
- 全件が 1 ページにあるか（`single_page`）、ページネーションがあるか

---

## Step 3. scrapling でセレクターを実際に試す

`GenericScraper` は内部で Scrapling を使用している。調査用スクリプトで挙動を確認するのが確実。

```python
from scrapling.fetchers import Fetcher
page = Fetcher().get('https://example.com/schedule')

# セレクターが正しいか確認
items = page.css('li.event-item')
print(f'件数: {len(items)}')
```

---

## Step 4. セレクターの特殊記法 (`_resolve_field`)

`selectors`（HTML型）および `response.mapping`（API型）の値で使用可能：

| 記法 | 説明 | 例 |
|---|---|---|
| (なし) | テキストを取得 | `div.title` |
| `::attr(名)` | 指定した属性値を取得 | `a::attr(href)` |
| `::regex(柄)` | 正規表現で抽出（グループ1優先） | `p::regex(開演\s*(\d+:\d+))` |

**API型のネストしたフィールド**: `response.mapping` ではドット記法でネストを辿れる。

```yaml
mapping:
  title: title.content       # item["title"]["content"] を取得
  start_time: schedule.start # item["schedule"]["start"] を取得
  ticket_url: link.link      # item["link"]["link"] を取得（相対URLは自動で絶対URLに変換）
```

---

## Step 5. dry-run で動作確認

設定を追加・修正したら、必ず `--dry-run` で意図通りに取れているか確認する。

```bash
uv run lt scrape --artist <name> --dry-run
```

- **0件の場合**: セレクターや API エンドポイント、ヘッダーが間違っている
- **重複がある場合**: API の期間指定が重なっている可能性がある（identity_key で重複除去されるが設定の見直しを推奨）
- **文字化け/パース失敗**: `date_format` が合っているか確認

---

## よくあるパターンと対処法

### パターン1: 動的なバージョン識別子を含む URL（Astro / Next.js SSR サイト等）

**症状**: JS バンドルで URL を組み立てており、ネットワークタブで見つけた URL に日時らしきハッシュが含まれる。

```
https://example.com/json/2605051820-AbCdEfGh/{year}_schedules.json
```

**原因**: Astro/Next.js のビルド時に生成されるキャッシュバスター。デプロイのたびに変わるため静的にハードコードすると翌日には壊れる。

**調査手順**:
1. ページの HTML ソースを確認し、そのハッシュがどこで定義されているかを探す
2. `<astro-island props="...">` や `<script id="__NEXT_DATA__">` などのインライン JSON に含まれることが多い

```python
import httpx, re
resp = httpx.get('https://example.com/schedule', follow_redirects=True)
# Astro の場合は HTML エンティティ（&quot;）でエンコードされていることに注意
m = re.search(r'&quot;versionDir&quot;:\[0,&quot;([^&]+)&quot;\]', resp.text)
print(m.group(1))  # → 2605051820-AbCdEfGh
```

**YAML 設定**:
```yaml
navigation:
  type: api_endpoint
  endpoint: /json/{version_dir}/{year}_schedules.json
  method: GET
  range_months: 3
  version_dir_regex: '&quot;versionDir&quot;:\[0,&quot;([^&]+)&quot;\]'
```

`version_dir_regex` を設定すると、スクレイピング実行時に `base_url` を取得してその場でハッシュを抽出し、`{version_dir}` に代入してから API を叩く。

**注意点**:
- HTML ソースを直接 `re.search` する場合、`"` が `&quot;` にエンティティエンコードされているケースがある。ブラウザの「ソース表示」ではなく Python/curl でのレスポンスで確認すること
- 正規表現が `None` を返す場合は、エンコード形式を確認する

---

### パターン2: 年次ファイルで全期間のイベントが一括配信される

**症状**: API エンドポイントが `/{year}_schedules.json` のような形式で、1リクエストで1年分のデータが返ってくる。

**注意点**:
- `range_months: 12` にすると同じ年次ファイルに12回リクエストが飛ぶ（内部で重複排除されるが無駄）
- `{month_start}` / `{month_end}` を使っても意味がない

**推奨設定**:
```yaml
navigation:
  endpoint: /json/{version_dir}/{year}_schedules.json
  range_months: 3   # 月単位で3ヶ月先まで見る。同年内は重複排除されるので実リクエストは1〜2回
```

同一 URL への重複リクエストはシステム側で自動排除される。年をまたぐ場合（例: 11月に設定すると翌年ファイルも必要）は自動で2リクエストになる。

---

### パターン3: 複数アーティスト分が混在した JSON

**症状**: レスポンスに他のアーティストや別カテゴリのイベントが大量に混じっている（例: ハロー！プロジェクト全体のスケジュール）。

**調査手順**:
1. レスポンスのアイテムを確認し、どのフィールドでアーティストやカテゴリを識別しているかを調べる
2. 目的のアーティストが含まれるアイテムの ID 値を確認する

```python
import httpx, json
from collections import Counter

data = httpx.get('https://example.com/json/2026_schedules.json').json()
items = data['items']

# カテゴリの種類を確認
print(Counter(i['category'] for i in items))

# タグからアーティストを特定し、そのアーティストIDを確認
target = [i for i in items if any('ArtistName' in t for t in i.get('tags', []))]
print(Counter(aid for i in target for aid in i.get('artistsSearch', [])))
```

**YAML 設定**:
```yaml
navigation:
  filter_artist_ids:
    - 36          # artistsSearch フィールドに含まれる ID でフィルタ
  filter_category: CONCERT   # category フィールドの値でフィルタ
```

---

### パターン4: 相対 URL としてリンクが返ってくる

**症状**: `link.link` や `url` フィールドが `/event/abc123/` のような相対パスになっている。

`source_url` / `ticket_url` に相対パスを設定した場合、スクレイパーが自動で `base_url_origin`（`https://example.com`）を付与してフル URL に変換する。追加の設定は不要。

```yaml
mapping:
  source_url: link.link   # /event/abc... → https://example.com/event/abc...
  ticket_url: link.link   # 同上
```
