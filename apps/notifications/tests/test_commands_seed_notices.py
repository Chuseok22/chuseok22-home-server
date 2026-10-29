from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.sejong import SejongNoticeItem
from apps.notifications.models import Notice, NoticeSource

_QUERY = '?mode=list&article.offset=0&articleLimit=10'
_BASE = 'https://www.sejong.ac.kr/kor/intro'


class TestSeedNotices(TestCase):
    def _run_seed(self, items: list[SejongNoticeItem] | None = None) -> None:
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = items or []
        with patch(
            'apps.notifications.management.commands.seed_notices.get_crawler',
            return_value=mock_crawler,
        ):
            call_command('seed_notices', stdout=StringIO())

    def test_SW중심대학_소스가_생성된다(self) -> None:
        self._run_seed()
        source = NoticeSource.objects.get(name='SW중심대학')
        self.assertEqual(source.crawler_type, 'sejong')
        self.assertEqual(source.icon, '💻')
        self.assertTrue(source.is_active)
        self.assertEqual(source.discord_webhook_url, '')
        self.assertEqual(
            source.url,
            'https://awcms2.sejong.ac.kr/sw/notice.do?mode=list&articleLimit=10&article.offset=0',
        )

    def test_기존_6개_소스의_이름_URL_아이콘이_유지된다(self) -> None:
        expected = {
            '일반공지': (f'{_BASE}/notice1.do{_QUERY}', '📌'),
            '학사공지': (f'{_BASE}/notice3.do{_QUERY}', '🎓'),
            '국제교류': (f'{_BASE}/notice4.do{_QUERY}', '🌐'),
            '취업': (f'{_BASE}/notice6.do{_QUERY}', '💼'),
            '장학': (f'{_BASE}/notice7.do{_QUERY}', '💰'),
            '채용모집': (f'{_BASE}/notice8.do{_QUERY}', '📋'),
        }
        self._run_seed()
        actual = {
            source.name: (source.url, source.icon)
            for source in NoticeSource.objects.filter(name__in=expected.keys())
        }
        self.assertEqual(actual, expected)

    def test_소스는_모두_7개다(self) -> None:
        self._run_seed()
        self.assertEqual(NoticeSource.objects.count(), 7)

    def test_두번_실행해도_소스가_중복_생성되지_않는다(self) -> None:
        self._run_seed()
        self._run_seed()
        self.assertEqual(NoticeSource.objects.count(), 7)

    def test_재실행시_admin에서_수정한_icon을_보존한다(self) -> None:
        NoticeSource.objects.create(
            name='SW중심대학',
            url='https://awcms2.sejong.ac.kr/sw/notice.do?mode=list&articleLimit=10&article.offset=0',
            crawler_type='sejong',
            icon='📖',
            is_active=True,
        )
        self._run_seed()
        self.assertEqual(NoticeSource.objects.get(name='SW중심대학').icon, '📖')

    def test_수집된_글은_알림_없이_저장된다(self) -> None:
        item = SejongNoticeItem(
            article_id='9001',
            title='t',
            url='https://awcms2.sejong.ac.kr/sw/notice.do?mode=view&articleNo=9001',
            published_at=date(2026, 10, 1),
        )
        self._run_seed([item])
        self.assertEqual(Notice.objects.count(), 7)
        self.assertEqual(Notice.objects.filter(is_notified=False).count(), 0)
