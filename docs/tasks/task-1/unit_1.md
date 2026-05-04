# Unit 1-1: データモデル・設定基盤

## 概要
全モジュールが依存する `LiveEvent` dataclass、YAML 設定スキーマ、`.env` 読み込みを確立する。
このタスクが完了するまで他のタスクは着手できない。

---

## ブランチ・PR

```bash
git checkout -b feature/m1-data-model
# 実装後
gh pr create --title "feat: データモデル・設定基盤" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/models/__init__.py` | 新規 |
| `src/models/event.py` | 新規 |
| `src/config.py` | 新規 |
| `config/artists.yaml` | 更新 |
| `.env.example` | 更新 |
| `pyproject.toml` | 更新 |

---

## 実装内容

### LiveEvent dataclass（src/models/event.py）

```python
@dataclass
class LiveEvent:
    title: str
    artist: str
    date: date | None
    start_time: str = ""
    venue: str = ""
    prefecture: str = ""
    ticket_url: str = ""
    ticket_price: str = ""
    other_artists: str = ""
    poster_url: str = ""
    source_url: str = ""
    fetch_status: str = "タイトル・日付のみ"

    def identity_key(self) -> tuple[str, str, date | None]:
        return (self.artist, self.title, self.date)

    def is_complete(self) -> bool:
        required = [self.venue, self.start_time, self.ticket_url]
        return all(f != "" for f in required)
```

### 設定ロード（src/config.py）

```python
def load_config() -> AppConfig:
    """artists.yaml + .env を読み込んで AppConfig を返す"""
```

---

## 統合後のインターフェース

他タスクはこのタスク完了後に以下を import して利用する：

```python
from src.models.event import LiveEvent
from src.config import load_config, ArtistConfig
```

---

## 人間の介入が必要な手順

なし（このタスクは純粋なコード）

---

## 依存タスク

なし（先頭タスク）

## 並列実装可能なタスク

なし（このタスク完了後に Unit 1-2 と Unit 1-3 が並列着手可能になる）

---

## 完了条件

- [ ] `LiveEvent` の全フィールドが定義されている
- [ ] `identity_key()` / `is_complete()` / `fetch_status` の自動計算が動作する
- [ ] `load_config()` で `artists.yaml` と `.env` が正しく読み込まれる
- [ ] `python -c "from src.models.event import LiveEvent; print(LiveEvent('test','artist',None))"` が通る

---

## レビュー観点

- `fetch_status` の自動計算ロジックが要件定義書のフォールバック戦略（Tier 1〜3）と整合しているか
- フィールドのデフォルト値が空文字（`""`）で統一されているか（`None` 混在禁止）
- `identity_key` の型が Notion Client（Unit 1-2）の dict キーと一致しているか
