from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class NoticeItem:
    article_id: str
    title: str
    url: str
    published_at: date | None
    application_start: date | None = None
    application_end: date | None = None
    operation_end: date | None = None


class BaseCrawler(ABC):
    def __init__(self, list_url: str) -> None:
        self.list_url = list_url

    @abstractmethod
    def crawl(self) -> list[NoticeItem]:
        """목록 페이지에서 공지 항목 리스트를 반환한다."""
        pass
