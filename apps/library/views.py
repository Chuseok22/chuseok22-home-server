import logging

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.library.serializers import StudyRoomSerializer
from apps.library.services.study_room import StudyRoomService

logger = logging.getLogger(__name__)


class StudyRoomListView(APIView):
    """학술정보원 전체 스터디룸 가용 현황 조회 API

    GET /api/v1/library/study-rooms/?date=YYYYMMDD
    - date 미지정 시 오늘(KST 기준) 조회
    - 인증: JWT Bearer 토큰
    """

    def get(self, request: Request) -> Response:
        reserve_date = request.query_params.get('date') or timezone.localdate().strftime('%Y%m%d')

        if not _is_valid_date(reserve_date):
            return Response(
                {'detail': 'date 파라미터는 YYYYMMDD 형식이어야 합니다.'},
                status=400,
            )

        service = StudyRoomService()
        rooms = service.fetch_all_rooms(reserve_date=reserve_date)

        if not rooms:
            return Response(
                {'detail': '스터디룸 정보를 가져올 수 없습니다. 잠시 후 다시 시도하세요.'},
                status=503,
            )

        return Response(StudyRoomSerializer(rooms, many=True).data)


def _is_valid_date(value: str) -> bool:
    from datetime import date
    if len(value) != 8 or not value.isdigit():
        return False
    try:
        date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        return True
    except ValueError:
        return False
