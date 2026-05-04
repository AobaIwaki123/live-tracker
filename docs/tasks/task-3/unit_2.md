# Unit 3-5: AI エンリッチメント（チケットサイト検索）

## 概要
Notion の `取得ステータス: 一部未取得` レコードを対象に、チケットサイトを検索して空欄フィールドを補完する。
opt-in（enrich コマンド実行時のみ動作）。

---

## ブランチ・PR

```bash
git checkout -b feature/m3-ai-enrichment
# 実装後
gh pr create --title "feat: AI エンリッチメント（チケットサイト検索・フィールド補完）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/enricher/__init__.py` | 新規 |
| `src/enricher/enricher.py` | 新規 |

---

## 実装内容

```python
TICKET_SITES = [
    "site:eplus.jp",
    "site:t.pia.jp",
    "site:l-tike.com",
]

class Enricher:
    def enrich(self, event: LiveEvent) -> dict[str, str]:
        """
        空欄フィールドを補完して diff を返す。
        補完できなかったフィールドは含めない。
        """
        query = f"{event.title} {event.artist} {event.date}"
        for site in TICKET_SITES:
            html = Fetcher.get(f"https://www.google.com/search?q={query}+{site}")
            extracted = self._extract_fields(html, event)
            if extracted:
                return extracted
        return {}

    def _extract_fields(self, html: str, event: LiveEvent) -> dict[str, str]:
        """AI Provider（Claude または Gemini）で HTML から空欄フィールドを抽出"""

    def enrich_all(
        self, records: list[LiveEvent]
    ) -> list[tuple[LiveEvent, dict]]:
        """全対象レコードを enrichしてNotion 更新し updated リストを返す"""
```

---

## 統合後のインターフェース

```python
from src.enricher.enricher import Enricher
from src.notion.client import NotionClient

notion = NotionClient()
enricher = Enricher()

incomplete = [e for e in notion.fetch_all().values()
              if e.fetch_status != "完全取得"]
updated = enricher.enrich_all(incomplete)
# Notion 更新は Enricher 内部で NotionClient.update() を呼ぶ
```

---

## 人間の介入が必要な手順

`ANTHROPIC_API_KEY` または `GEMINI_API_KEY` のいずれかが `.env` に設定済みであること

---

## 依存タスク

- task-2/unit_1（M1-P2: Notion Client — レコード取得・更新に使用）
- task-2/unit_3（AI Provider — フィールド抽出に使用）

## 並列実装可能なタスク

- task-3/unit_1（M1-P4: CLI 骨格）と同時着手可能

---

## 完了条件

- [ ] `一部未取得` のレコードに対してチケットサイト検索が実行される
- [ ] 補完できたフィールドのみ Notion レコードが更新される
- [ ] 補完後に `取得ステータス` が適切に更新される（全フィールド揃えば `完全取得`）
- [ ] 検索・抽出に失敗した場合、既存 Notion レコードが壊れない

---

## レビュー観点

- Google 検索のスクレイピングが失敗したときのフォールバックがあるか
- `_extract_fields` が空のフィールドのみを補完対象とし、既存値を上書きしないか
- AI Provider の呼び出しコストを抑えるため、必要なフィールドのみ問い合わせているか
- 検索結果が無関係なページを返したとき、誤ったデータで上書きしないか（信頼度チェック）
