from __future__ import annotations

from abc import ABC, abstractmethod

from src.config import ArtistConfig
from src.models.event import LiveEvent


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        """Scrape live events for the given artist config."""
        ...
