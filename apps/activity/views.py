from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from apps.activity.models import GithubActivity
from apps.activity.serializers import ActivityItemSerializer


class ActivityPagination(PageNumberPagination):
    """활동 목록 전용 페이지네이션 (page_size 고정)"""
    page_size = 20


@extend_schema(
    summary='GitHub 활동 목록 조회',
    description=(
        'DB에 캐싱된 GitHub 활동 이력을 발생 시각(occurred_at) 내림차순으로 반환한다. '
        '인증 없이 접근 가능. 페이지당 20건 고정이며 ?page= 파라미터로 페이지를 지정한다. '
        '실제 수집은 management command fetch_github_activities가 수행한다.'
    ),
    parameters=[
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='페이지 번호 (기본값: 1)',
        ),
    ],
    responses={200: ActivityItemSerializer(many=True)},
)
class ActivityListView(ListAPIView):
    queryset = GithubActivity.objects.all().order_by('-occurred_at')
    serializer_class = ActivityItemSerializer
    permission_classes = [AllowAny]
    pagination_class = ActivityPagination
