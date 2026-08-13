from .base import BaseExamCrawler
from .hrdkorea_api import HrdKoreaApiCrawler
from .manual import ManualCrawler

# 새 크롤러 추가 시 여기에 등록한다
CRAWLER_REGISTRY: dict[str, type[BaseExamCrawler]] = {
    'hrdkorea_api': HrdKoreaApiCrawler,
    'manual': ManualCrawler,
}


def get_crawler(crawler_type: str) -> BaseExamCrawler:
    cls = CRAWLER_REGISTRY.get(crawler_type)
    if cls is None:
        raise ValueError(f'지원하지 않는 크롤러 타입: {crawler_type}')
    return cls()
