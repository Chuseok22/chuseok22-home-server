import logging

from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def delete_expired_records(queryset: QuerySet, label: str) -> int:
    """만료 조건으로 이미 필터링된 queryset을 삭제하고 삭제 건수를 반환한다."""
    count, _ = queryset.delete()
    logger.info('%s 정리 완료: %d건 삭제', label, count)
    return count
