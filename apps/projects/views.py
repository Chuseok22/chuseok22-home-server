from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project, ProjectCategory
from apps.projects.serializers import ProjectSerializer

_VALID_CATEGORIES = {c.value for c in ProjectCategory}


class ProjectListView(APIView):
    """프로젝트 목록 공개 조회 API"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary='프로젝트 목록 조회',
        description='포트폴리오 프로젝트 목록을 반환한다. category 미지정 시 전체를 반환한다.',
        parameters=[
            OpenApiParameter(
                name='category',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='team / side / open_source',
                enum=[c.value for c in ProjectCategory],
            ),
        ],
        responses={
            200: ProjectSerializer(many=True),
            400: OpenApiResponse(description='유효하지 않은 category 값'),
        },
        tags=['projects'],
    )
    def get(self, request: Request) -> Response:
        qs = Project.objects.all()
        category = request.query_params.get('category')
        if category:
            if category not in _VALID_CATEGORIES:
                return Response(
                    {'detail': f'유효하지 않은 category입니다. 허용값: {", ".join(sorted(_VALID_CATEGORIES))}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(category=category)
        return Response(ProjectSerializer(qs, many=True).data)
