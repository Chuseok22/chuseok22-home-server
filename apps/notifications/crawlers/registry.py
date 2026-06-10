from .base import BaseCrawler
from .sejong import SejongNoticeCrawler

# 새 사이트 추가 시 여기에 크롤러 클래스를 등록한다
CRAWLER_REGISTRY: dict[str, type[BaseCrawler]] = {
    'sejong_haksa': SejongNoticeCrawler,
}


def get_crawler(crawler_type: str, url: str) -> BaseCrawler:
    cls = CRAWLER_REGISTRY.get(crawler_type)
    if cls is None:
        raise ValueError(f'지원하지 않는 크롤러 타입: {crawler_type}')
    return cls(url)
