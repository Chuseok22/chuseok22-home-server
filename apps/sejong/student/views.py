import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sejong.student.serializers import StudentSearchResponseSerializer
from apps.sejong.student.services.student_search import StudentSearchService

logger = logging.getLogger(__name__)


class StudentSearchView(APIView):
    """세종대학교 학생 조회 API"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='세종대학교 학생 조회',
        description=(
            'classic.sejong.ac.kr Classic 시스템을 통해 학생 정보를 조회한다.\n\n'
            '**이름 검색**: `?name=백지훈` — 동명이인이 여럿일 경우 목록 반환.\n\n'
            '**학번 검색**: `?student_no=22011315` — 단일 결과 반환.\n\n'
            '`name`과 `student_no` 중 정확히 하나만 전달해야 한다. '
            '둘 다 전달하거나 둘 다 없으면 400을 반환한다.\n\n'
            'JWT 인증 필수.'
        ),
        parameters=[
            OpenApiParameter(
                name='name',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='학생 이름 (예: 백지훈)',
            ),
            OpenApiParameter(
                name='student_no',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='학번 (예: 22011315)',
            ),
        ],
        responses={
            200: StudentSearchResponseSerializer,
            400: OpenApiResponse(description='name 또는 student_no 중 하나만 전달해야 함'),
            503: OpenApiResponse(description='세종대 Classic 서비스 응답 없음'),
        },
        tags=['sejong'],
    )
    def get(self, request: Request) -> Response:
        name = request.query_params.get('name', '').strip()
        student_no = request.query_params.get('student_no', '').strip()

        if bool(name) == bool(student_no):
            return Response(
                {'detail': 'name 또는 student_no 중 정확히 하나를 전달해야 합니다.'},
                status=400,
            )

        service = StudentSearchService()

        if name:
            results = service.search_by_name(name)
        else:
            results = service.search_by_student_no(student_no)

        if results is None:
            return Response(
                {'detail': '세종대 Classic 서비스에 연결할 수 없습니다. 잠시 후 다시 시도하세요.'},
                status=503,
            )

        data = StudentSearchResponseSerializer({'results': results}).data
        return Response(data)
