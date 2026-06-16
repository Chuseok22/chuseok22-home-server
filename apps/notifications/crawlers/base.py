from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseNoticeItem:
    """모든 공지 아이템의 공통 필드"""
    article_id: str
    title: str
    url: str


class BaseCrawler(ABC):
    def __init__(self, list_url: str) -> None:
        self.list_url = list_url

    @abstractmethod
    def crawl(self) -> list[BaseNoticeItem]:
        """목록 페이지에서 공지 항목 리스트를 반환한다."""
        pass

    def crawl_detail(self, url: str) -> BaseNoticeItem | None:
        """상세 페이지에서 전체 필드를 채운 아이템을 반환한다. 기본값은 None (미지원)."""
        return None
