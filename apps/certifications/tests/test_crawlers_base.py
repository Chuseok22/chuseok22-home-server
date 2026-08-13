import pytest
from datetime import date

from apps.certifications.crawlers.base import ExamRoundItem
from apps.certifications.crawlers.manual import ManualCrawler
from apps.certifications.crawlers.registry import CRAWLER_REGISTRY, get_crawler


def test_manual_크롤러는_항상_빈_리스트를_반환한다() -> None:
    crawler = ManualCrawler()

    result = crawler.crawl('아무값')

    assert result == []


def test_exam_round_item_필드() -> None:
    item = ExamRoundItem(
        round_name='2026년 1회 필기',
        registration_start=date(2026, 1, 5),
        registration_end=date(2026, 1, 9),
        exam_date=date(2026, 2, 7),
        result_announcement_date=date(2026, 3, 4),
        source_url='https://www.q-net.or.kr/crf021.do',
    )

    assert item.round_name == '2026년 1회 필기'


def test_registry에_manual이_등록되어_있다() -> None:
    assert 'manual' in CRAWLER_REGISTRY


def test_get_crawler는_manual_인스턴스를_반환한다() -> None:
    crawler = get_crawler('manual')

    assert isinstance(crawler, ManualCrawler)


def test_get_crawler는_알수없는_타입에_ValueError() -> None:
    with pytest.raises(ValueError):
        get_crawler('존재하지않는타입')
