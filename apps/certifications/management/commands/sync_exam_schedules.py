import logging

from django.core.management.base import BaseCommand

from apps.certifications.crawlers import get_crawler
from apps.certifications.models import CertificationDefinition, ExamSchedule

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '활성화된 자격증의 회차별 시험 일정을 크롤러로 동기화한다 (manual 타입은 건너뜀)'

    def handle(self, *args, **options) -> None:
        certifications = CertificationDefinition.objects.filter(
            is_active=True, is_always_open=False,
        ).exclude(crawler_type='manual')
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

        # round_name별 기존 일정을 미리 조회해둔다 — 접수 시작/마감일이 바뀌었는지 판단해
        # 이미 True인 알림 플래그를 재설정해야 하기 때문이다(그렇지 않으면 날짜가 바뀐 뒤에도
        # 예전 날짜 기준으로 이미 보낸 것으로 간주돼 새 날짜에 대한 알림이 영영 발송되지 않는다).
        existing_by_round_name = {
            schedule.round_name: schedule
            for schedule in ExamSchedule.objects.filter(certification=certification)
        }

        updated_count = 0
        for round_item in rounds:
            defaults = {
                'registration_start': round_item.registration_start,
                'registration_end': round_item.registration_end,
                'exam_date': round_item.exam_date,
                'result_announcement_date': round_item.result_announcement_date,
                'source_url': round_item.source_url,
            }
            existing = existing_by_round_name.get(round_item.round_name)
            if existing is not None:
                if existing.registration_start != round_item.registration_start:
                    defaults['registration_open_notified'] = False
                if existing.registration_end != round_item.registration_end:
                    defaults['registration_deadline_notified'] = False
            ExamSchedule.objects.update_or_create(
                certification=certification,
                round_name=round_item.round_name,
                defaults=defaults,
            )
            updated_count += 1
        self.stdout.write(f'[{certification.name}] {updated_count}건 동기화 완료')
