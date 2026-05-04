"""LiveEvent dataclass — イベント情報のデータモデル。(参照: docs/basic-design.md § 5. データモデル)"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class LiveEvent:
    """ライブイベント情報を保持するデータクラス。

    重複判定キーは ``(artist, title, date)``。
    ``fetch_status`` は ``__post_init__`` でフィールド充足度から自動算出される。

    Attributes:
        title: 公演名。Tier 1 メインページから取得。
        artist: アーティスト識別子。config から設定。
        date: 開催日。Tier 1 メインページから取得。
        start_time: 開始時刻。Tier 1〜2。
        venue: 会場名。Tier 1〜2。
        prefecture: 都道府県。Tier 2〜3（会場から導出）。
        ticket_url: チケット URL。Tier 1〜2。
        ticket_price: チケット料金。Tier 3 チケットサイト。
        other_artists: 出演アーティスト。Tier 2〜3。
        poster_url: ポスター画像 URL。Tier 2 詳細ページ。
        source_url: スクレイピング元 URL。config + Tier 1。
        id: API レスポンスから取得した外部 ID。api_endpoint タイプで使用。
        fetch_status: 取得完了度。詳細取得済み / 詳細一部取得 / タイトル・日付のみ。
    """

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
    id: str = ""
    fetch_status: str = field(init=False)

    def __post_init__(self) -> None:
        self.fetch_status = self._compute_fetch_status()

    def _compute_fetch_status(self) -> str:
        if self.venue and self.start_time and self.ticket_url:
            return "詳細取得済み"
        if self.venue or self.start_time:
            return "詳細一部取得"
        return "タイトル・日付のみ"

    def identity_key(self) -> tuple[str, str, date | None]:
        """Return the dedup key ``(artist, title, date)``."""
        return (self.artist, self.title, self.date)

    def is_complete(self) -> bool:
        """Return True when venue, start_time, and ticket_url are all populated."""
        return all(f != "" for f in [self.venue, self.start_time, self.ticket_url])
