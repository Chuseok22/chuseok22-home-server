from django.test import TestCase

from apps.notifications.crawlers.dacon import DaconItem
from apps.notifications.management.commands.check_new_notices import Command


class TestCheckNewNoticesGetPublishedAt(TestCase):
    def setUp(self) -> None:
        self.command = Command()

    def test_dacon_아이템은_게시일_없음(self) -> None:
        item = DaconItem(
            article_id='236727',
            title='대회 제목',
            url='https://dacon.io/competitions/official/236727/overview/',
            status='참가신청중',
            participant_count=100,
            tags=[],
        )
        result = self.command._get_published_at(item)
        self.assertIsNone(result)
