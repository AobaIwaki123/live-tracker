"""LocalStore.upsert_many_diff の差分検出ロジックをテストする。

実際の SQLite ファイルを使い、upsert・SELECT の SQL ロジックも含めて通す。
"""
import pytest
from datetime import date

from src.models.event import LiveEvent
from src.store.local_store import LocalStore


def _event(**kwargs) -> LiveEvent:
    defaults = dict(
        artist="test-artist",
        title="テストライブ",
        date=date(2026, 6, 1),
        venue="",
        start_time="",
        ticket_url="",
        ticket_price="",
        other_artists="",
        poster_url="",
        source_url="",
    )
    defaults.update(kwargs)
    return LiveEvent(**defaults)


@pytest.fixture
def store(tmp_path):
    return LocalStore(db_path=str(tmp_path / "events.db"))


class TestInitialRun:
    def test_all_events_created_on_first_run(self, store):
        """初回実行（DB空）では全イベントが created に分類される。"""
        events = [_event(title="ライブA"), _event(title="ライブB")]
        created, updated = store.upsert_many_diff(events)

        assert len(created) == 2
        assert len(updated) == 0

    def test_events_persisted_after_first_run(self, store):
        """初回 upsert 後、DB に全件保存されている。"""
        events = [_event(title="ライブA"), _event(title="ライブB")]
        store.upsert_many_diff(events)

        all_events = store.get_all()
        assert len(all_events) == 2


class TestSecondRunNoChange:
    def test_no_notification_when_nothing_changed(self, store):
        """2回目で内容が変化しない場合、created / updated ともに空。"""
        events = [_event(venue="渋谷WWWX")]
        store.upsert_many_diff(events)

        created, updated = store.upsert_many_diff(events)

        assert created == []
        assert updated == []


class TestFieldUpdate:
    def test_venue_filled_triggers_updated(self, store):
        """前回は空だった venue が今回埋まったら updated に分類される。"""
        store.upsert_many_diff([_event(venue="")])

        created, updated = store.upsert_many_diff([_event(venue="Zepp DiverCity")])

        assert created == []
        assert len(updated) == 1
        assert updated[0].venue == "Zepp DiverCity"

    def test_ticket_url_added_triggers_updated(self, store):
        """チケットURL が新たに取得できたら updated に分類される。"""
        store.upsert_many_diff([_event(ticket_url="")])

        created, updated = store.upsert_many_diff(
            [_event(ticket_url="https://l-tike.com/xxxx")]
        )

        assert len(updated) == 1

    def test_empty_incoming_field_does_not_trigger_updated(self, store):
        """新スクレイプで venue が空（未公開）でも、既存データがあれば updated に入らない。"""
        store.upsert_many_diff([_event(venue="Zepp DiverCity")])

        # 次回スクレイプでサイトが会場を出していない場合
        created, updated = store.upsert_many_diff([_event(venue="")])

        assert created == []
        assert updated == []

    def test_db_retains_existing_value_when_incoming_is_empty(self, store):
        """空フィールドで upsert しても DB の既存値は保持される。"""
        store.upsert_many_diff([_event(venue="Zepp DiverCity")])
        store.upsert_many_diff([_event(venue="")])

        saved = store.get_all()[0]
        assert saved.venue == "Zepp DiverCity"


class TestNewEventOnSubsequentRun:
    def test_new_event_in_second_run_is_created(self, store):
        """2回目に追加されたイベントは created に分類される。"""
        store.upsert_many_diff([_event(title="既存ライブ")])

        created, updated = store.upsert_many_diff(
            [_event(title="既存ライブ"), _event(title="新規ライブ")]
        )

        assert len(created) == 1
        assert created[0].title == "新規ライブ"
        assert updated == []

    def test_identity_key_uses_artist_title_date(self, store):
        """同タイトルでも日付が異なれば別イベントとして created に入る。"""
        store.upsert_many_diff([_event(title="定期公演", date=date(2026, 6, 1))])

        created, updated = store.upsert_many_diff(
            [_event(title="定期公演", date=date(2026, 7, 1))]
        )

        assert len(created) == 1
        assert created[0].date == date(2026, 7, 1)
