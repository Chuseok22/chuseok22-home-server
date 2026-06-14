from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project, ProjectCategory
from apps.projects.serializers import ProjectSerializer


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
        responses={200: ProjectSerializer(many=True)},
        tags=['projects'],
    )
    def get(self, request: Request) -> Response:
        qs = Project.objects.all()
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return Response(ProjectSerializer(qs, many=True).data)
