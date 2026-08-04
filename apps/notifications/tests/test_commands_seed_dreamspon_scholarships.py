from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.notifications.crawlers.dreamspon import DreamsponItem
from apps.notifications.models import Notice, NoticeSource


class TestSeedDreamsponScholarships(TestCase):
    def _run_with_items_by_url(self, items_by_url: dict[str, list[DreamsponItem]]) -> None:
        def _get_crawler(crawler_type: str, url: str) -> MagicMock:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = items_by_url.get(url, [])
            return mock_crawler

        with patch(
            'apps.notifications.management.commands.seed_dreamspon_scholarships.get_crawler',
            side_effect=_get_crawler,
        ):
            call_command('seed_dreamspon_scholarships', stdout=StringIO())

    def test_소스_2건_생성(self) -> None:
        self._run_with_items_by_url({})

        scholarship = NoticeSource.objects.get(name='일반장학금')
        self.assertEqual(scholarship.crawler_type, 'dreamspon')
        self.assertEqual(scholarship.url, 'https://www.dreamspon.com/scholarship/list.html')
        self.assertTrue(scholarship.is_active)

        dream = NoticeSource.objects.get(name='드림장학금')
        self.assertEqual(dream.crawler_type, 'dreamspon')
        self.assertEqual(dream.url, 'https://www.dreamspon.com/dreamscholarship/list.html')
        self.assertTrue(dream.is_active)

    def test_재실행시_소스_중복_생성_안함(self) -> None:
        self._run_with_items_by_url({})
        self._run_with_items_by_url({})
        self.assertEqual(NoticeSource.objects.filter(crawler_type='dreamspon').count(), 2)

    def test_기존_항목_is_notified_true로_저장(self) -> None:
        item = DreamsponItem(
            article_id='9130', title='장학금 제목',
            url='https://www.dreamspon.com/scholarship/view.html?idx=9130',
            organization='에디티지', hit_count=1294, scholarship_type=None,
            target=None, recruit_count=None, benefit=None,
            application_start=None, application_end=None, tags=[],
        )
        self._run_with_items_by_url({
            'https://www.dreamspon.com/scholarship/list.html': [item],
        })

        notice = Notice.objects.get(source__name='일반장학금', article_id='9130')
        self.assertTrue(notice.is_notified)
        self.assertEqual(notice.title, '장학금 제목')
        self.assertIsNone(notice.published_at)

    def test_중복_항목_재저장_안함(self) -> None:
        item = DreamsponItem(
            article_id='9130', title='장학금', url='https://www.dreamspon.com/scholarship/view.html?idx=9130',
            organization=None, hit_count=None, scholarship_type=None,
            target=None, recruit_count=None, benefit=None,
            application_start=None, application_end=None, tags=[],
        )
        items_by_url = {'https://www.dreamspon.com/scholarship/list.html': [item]}
        self._run_with_items_by_url(items_by_url)
        self._run_with_items_by_url(items_by_url)

        self.assertEqual(Notice.objects.filter(source__name='일반장학금').count(), 1)
