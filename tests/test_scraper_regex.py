"""GenericScraper._resolve_field の ::regex() 擬似要素をテストする。

scrapling の実 HTML パースを通して動作を確認する。
"""
import pytest

from src.scrapers.generic import GenericScraper


def _page(html: str):
    """文字列 HTML を scrapling の Selector オブジェクトに変換する。"""
    from scrapling import Selector
    return Selector(html)


@pytest.fixture
def scraper():
    return GenericScraper()


class TestResolveFieldRegex:
    def test_regex_extracts_capture_group(self, scraper):
        """::regex() でキャプチャグループ 1 の内容を返す。"""
        page = _page("<p class='info'>🏰会場：Zepp DiverCity<br>住所テキスト</p>")
        selectors = {"venue": "p.info::regex(🏰会場：([^\n]+))"}

        result = scraper._resolve_field(page, selectors, "venue")

        assert result == "Zepp DiverCity"

    def test_regex_no_match_returns_empty(self, scraper):
        """パターンが一致しない場合は空文字を返す。"""
        page = _page("<p class='info'>会場情報なし</p>")
        selectors = {"venue": "p.info::regex(🏰会場：([^\n]+))"}

        result = scraper._resolve_field(page, selectors, "venue")

        assert result == ""

    def test_regex_with_nested_elements(self, scraper):
        """br や b タグを挟んだ複数行テキストからも抽出できる。"""
        html = (
            "<p class='mt-2'>2026年4月29日<br>"
            "<b>公演タイトル</b><br>"
            "🏰会場：Zepp DiverCity<br>"
            "🕑時間：開場16:30／開演17:30</p>"
        )
        page = _page(html)

        venue = scraper._resolve_field(page, {"venue": "p.mt-2::regex(🏰会場：([^\n]+))"}, "venue")
        start_time = scraper._resolve_field(page, {"start_time": "p.mt-2::regex(開演(\\d+:\\d+))"}, "start_time")

        assert venue == "Zepp DiverCity"
        assert start_time == "17:30"

    def test_attr_selector_still_works(self, scraper):
        """::attr() が引き続き動作することを回帰確認する。"""
        page = _page('<p><a href="https://example.com/ticket">チケット</a></p>')
        selectors = {"ticket_url": "a::attr(href)"}

        result = scraper._resolve_field(page, selectors, "ticket_url")

        assert result == "https://example.com/ticket"
