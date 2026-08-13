import logging

from django.core.management.base import BaseCommand

from apps.certifications.crawlers import get_crawler
from apps.certifications.models import CertificationDefinition, ExamSchedule

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '활성화된 자격증의 회차별 시험 일정을 크롤러로 동기화한다 (manual 타입은 건너뜀)'

    def handle(self, *args, **options) -> None:
        certifications = CertificationDefinition.objects.filter(is_active=True).exclude(crawler_type='manual')
        if not certifications.exists():
            self.stdout.write('동기화 대상 자격증이 없습니다.')
            return

        for certification in certifications:
            self._sync_certification(certification)

    def _sync_certification(self, certification: CertificationDefinition) -> None:
        try:
            crawler = get_crawler(certification.crawler_type)
        except ValueError as e:
            logger.error('크롤러 생성 실패 (certification=%s): %s', certification.name, e)
            self.stderr.write(str(e))
            return

        rounds = crawler.crawl(certification.crawler_source_id)
        if not rounds:
            self.stdout.write(f'[{certification.name}] 수집된 일정 없음')
            return

        updated_count = 0
        for round_item in rounds:
            ExamSchedule.objects.update_or_create(
                certification=certification,
                round_name=round_item.round_name,
                defaults={
                    'registration_start': round_item.registration_start,
                    'registration_end': round_item.registration_end,
                    'exam_date': round_item.exam_date,
                    'result_announcement_date': round_item.result_announcement_date,
                    'source_url': round_item.source_url,
                },
            )
            updated_count += 1
        self.stdout.write(f'[{certification.name}] {updated_count}건 동기화 완료')
