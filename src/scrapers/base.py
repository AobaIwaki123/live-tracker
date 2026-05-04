"""スクレイパー抽象基底クラス。(参照: docs/basic-design.md § 4-2. GenericScraper)"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.config import ArtistConfig
from src.models.event import LiveEvent


class BaseScraper(ABC):
    """すべてのスクレイパーが実装すべき抽象基底クラス。"""

    @abstractmethod
    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        """Scrape live events for the given artist config.

        Args:
            config: 対象アーティストの設定。

        Returns:
            スクレイピングで取得した LiveEvent リスト。
        """
        ...
