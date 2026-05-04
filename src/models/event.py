from dataclasses import dataclass, field
from datetime import date


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
        return (self.artist, self.title, self.date)

    def is_complete(self) -> bool:
        return all(f != "" for f in [self.venue, self.start_time, self.ticket_url])
