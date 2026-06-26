import logging
from datetime import date

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sejong.library.models import ReservationAttendee, ReservationHistory
from apps.sejong.library.serializers import (
    ReservationAttendeeSerializer,
    StudyRoomReserveRequestSerializer,
    StudyRoomReserveResponseSerializer,
    StudyRoomSerializer,
)
from apps.sejong.library.services.study_room import StudyRoomService
from apps.sejong.library.services.study_room_reservation import (
    AttendeeParams,
    ReservationParams,
    StudyRoomReservationService,
)

logger = logging.getLogger(__name__)


class StudyRoomListView(APIView):
    """학술정보원 전체 스터디룸 가용 현황 조회 API"""

    @extend_schema(
        summary='스터디룸 가용 현황 조회',
        description='학술정보원 전체 스터디룸의 날짜별 예약 가능 슬롯을 조회한다. date 미지정 시 오늘(KST 기준)을 사용한다.',
        parameters=[
            OpenApiParameter(
                name='date',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='조회 날짜 (YYYYMMDD). 미지정 시 오늘.',
                examples=[
                    OpenApiExample('오늘', value='20260613'),
                ],
            ),
        ],
        responses={
            200: StudyRoomSerializer(many=True),
            400: OpenApiResponse(description='date 파라미터 형식 오류 (YYYYMMDD 아닌 경우)'),
            503: OpenApiResponse(description='학술정보원 서비스 응답 없음'),
        },
        tags=['library'],
    )
    def get(self, request: Request) -> Response:
        reserve_date = request.query_params.get('date') or timezone.localdate().strftime('%Y%m%d')

        if not _is_valid_date(reserve_date):
            return Response(
                {'detail': 'date 파라미터는 YYYYMMDD 형식이어야 합니다.'},
                status=400,
            )

        try:
            service = StudyRoomService()
            rooms = service.fetch_all_rooms(reserve_date=reserve_date)
        except ValueError as e:
            logger.error('스터디룸 서비스 설정 오류 (자격증명 누락): %s', e)
            return Response({'detail': '서비스 설정이 올바르지 않습니다.'}, status=503)

        if not rooms:
            logger.warning('스터디룸 정보 조회 실패 (date=%s). 서비스 응답 없음 또는 인증 실패.', reserve_date)
            return Response(
                {'detail': '스터디룸 정보를 가져올 수 없습니다. 잠시 후 다시 시도하세요.'},
                status=503,
            )

        return Response(StudyRoomSerializer(rooms, many=True).data)


class StudyRoomReserveView(APIView):
    """스터디룸 예약 API"""

    @extend_schema(
        summary='스터디룸 예약',
        description=(
            '스터디룸을 예약한다.\n\n'
            '**auto_select=false (기본)**: `room_no`, `room_gb`, `seat_cnt`, `sroom_title`, `room_name`, `seq` 모두 필수.\n\n'
            '**auto_select=true**: 위 필드 불필요. `reserve_date`, `start_time`, `use_time`, `attendees`만 전달하면 '
            '인원수 조건(`ceil(seat_cnt/2) ≤ 인원 ≤ seat_cnt`)을 만족하는 가용 룸을 자동 선택해 예약한다.\n\n'
            '예약 성공 시 HTTP 200, 가용 룸 없음·예약 실패 시 HTTP 422를 반환한다. '
            '두 경우 모두 응답 body 구조는 동일하다.'
        ),
        request=StudyRoomReserveRequestSerializer,
        responses={
            200: StudyRoomReserveResponseSerializer,
            400: OpenApiResponse(description='입력 검증 오류 (필수 필드 누락, 날짜/시간 형식 오류 등)'),
            422: StudyRoomReserveResponseSerializer,
            503: OpenApiResponse(description='예약 서비스 초기화 실패 (환경변수 미설정 등)'),
        },
        tags=['library'],
    )
    def post(self, request: Request) -> Response:
        serializer = StudyRoomReserveRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        attendees = tuple(
            AttendeeParams(student_id=a['student_id'], name=a['name'])
            for a in data['attendees']
        )

        try:
            service = StudyRoomReservationService()
            if data['auto_select']:
                result = service.auto_reserve(
                    reserve_date=data['reserve_date'],
                    start_time=data['start_time'],
                    use_time=data['use_time'],
                    attendees=attendees,
                )
            else:
                params = ReservationParams(
                    room_no=data['room_no'],
                    room_gb=data['room_gb'],
                    seat_cnt=data['seat_cnt'],
                    sroom_title=data['sroom_title'],
                    room_name=data['room_name'],
                    seq=data['seq'],
                    reserve_date=data['reserve_date'],
                    start_time=data['start_time'],
                    use_time=data['use_time'],
                    attendees=attendees,
                )
                result = service.reserve(params)
        except ValueError as e:
            logger.error('예약 서비스 설정 오류 (자격증명 누락): %s', e)
            return Response({'detail': '서비스 설정이 올바르지 않습니다.'}, status=503)

        try:
            # 성공/실패 관계없이 이력 저장
            ReservationHistory.objects.create(
                room_no=result.room_no,
                room_name=result.room_name,
                reserve_date=data['reserve_date'],
                start_time=data['start_time'],
                use_time=data['use_time'],
                attendees_json=[
                    {'student_id': a.student_id, 'name': a.name}
                    for a in attendees
                ],
                result_code=result.result_code,
                result_message=result.result_message,
            )

            # 예약 성공 시 새 참여자만 DB 저장
            if result.success:
                for attendee in attendees:
                    ReservationAttendee.objects.get_or_create(
                        student_id=attendee.student_id,
                        defaults={'name': attendee.name},
                    )
        except Exception as e:
            # DB 후처리 실패가 예약 결과 응답을 막아서는 안 됨
            logger.error('예약 후처리 DB 저장 실패 (result_code=%s): %s', result.result_code, e)

        status_code = 200 if result.success else 422
        return Response(
            StudyRoomReserveResponseSerializer(result).data,
            status=status_code,
        )


class ReservationAttendeeListCreateView(APIView):
    """저장된 참여자 조회 및 추가"""

    @extend_schema(
        summary='저장된 참여자 목록 조회',
        description='예약에 사용할 참여자(학번+이름) 목록을 조회한다.',
        responses={200: ReservationAttendeeSerializer(many=True)},
        tags=['library'],
    )
    def get(self, request: Request) -> Response:
        attendees = ReservationAttendee.objects.all()
        return Response(ReservationAttendeeSerializer(attendees, many=True).data)

    @extend_schema(
        summary='참여자 추가',
        description=(
            '참여자(학번+이름)를 저장한다. 동일 학번이 이미 존재하면 추가 없이 기존 레코드를 반환한다.\n\n'
            '신규 등록 시 HTTP 201, 기존 존재 시 HTTP 200을 반환한다.'
        ),
        request=ReservationAttendeeSerializer,
        responses={
            201: ReservationAttendeeSerializer,
            200: ReservationAttendeeSerializer,
            400: OpenApiResponse(description='입력 검증 오류'),
        },
        tags=['library'],
    )
    def post(self, request: Request) -> Response:
        serializer = ReservationAttendeeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        attendee, created = ReservationAttendee.objects.get_or_create(
            student_id=data['student_id'],
            defaults={'name': data['name']},
        )
        status_code = 201 if created else 200
        return Response(ReservationAttendeeSerializer(attendee).data, status=status_code)


class ReservationAttendeeDestroyView(APIView):
    """저장된 참여자 삭제"""

    @extend_schema(
        summary='참여자 삭제',
        description='저장된 참여자를 삭제한다.',
        responses={
            204: OpenApiResponse(description='삭제 성공 (body 없음)'),
            404: OpenApiResponse(description='참여자를 찾을 수 없음'),
        },
        tags=['library'],
    )
    def delete(self, request: Request, pk: int) -> Response:
        try:
            attendee = ReservationAttendee.objects.get(pk=pk)
        except ReservationAttendee.DoesNotExist:
            return Response({'detail': '참여자를 찾을 수 없습니다.'}, status=404)

        attendee.delete()
        return Response(status=204)


def _is_valid_date(value: str) -> bool:
    if len(value) != 8 or not value.isdigit():
        return False
    try:
        date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        return True
    except ValueError:
        return False
