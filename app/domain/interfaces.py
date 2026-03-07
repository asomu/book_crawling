from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.schemas import FetchBookResult, HealthcheckResult


class CrawlerAdapter(ABC):
    @abstractmethod
    def login(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_book(self, isbn: str) -> FetchBookResult:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> HealthcheckResult:
        raise NotImplementedError
