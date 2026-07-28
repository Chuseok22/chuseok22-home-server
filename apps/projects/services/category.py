from dataclasses import dataclass

from django.db.models import Count, QuerySet

from apps.projects.models import Project, ProjectCategory


@dataclass(frozen=True)
class ProjectCategorySidebarItem:
    """프로젝트 목록 사이드바 표시용 카테고리 항목."""

    id: int
    name: str
    project_count: int


def get_project_category_sidebar_items() -> list[ProjectCategorySidebarItem]:
    """프로젝트가 1개 이상 있는 카테고리만, order 순으로 반환한다.
    order 값이 같은 카테고리가 있을 수 있어(Admin에서 자유 입력) id를 2차 정렬 기준으로 둬
    ProjectCategory.Meta.ordering(['order', 'id'])과 동일한 순서를 보장한다."""
    categories = ProjectCategory.objects.annotate(
        project_count=Count('projects'),
    ).filter(project_count__gt=0).order_by('order', 'id')
    return [
        ProjectCategorySidebarItem(id=category.id, name=category.name, project_count=category.project_count)
        for category in categories
    ]


def filter_projects_by_category_id(category_id: int | None) -> QuerySet[Project]:
    """category_id가 None이면 전체를 반환한다.
    존재하지 않는 category_id는 필터링 결과가 자연히 빈 QuerySet이 되므로 별도 존재 확인이 필요 없다.
    select_related로 category/status를 미리 가져와 카드 렌더링 시 N+1 쿼리를 막고,
    category_id를 정렬 타이브레이커로 추가해 category.order 값이 같은 카테고리가 있어도
    {% regroup %}가 프로젝트를 카테고리별로 안정적으로 묶도록 한다(순서가 흔들리면 같은
    카테고리 섹션 헤더가 중복 렌더링될 수 있음).
    """
    projects = Project.objects.select_related('category', 'status')
    if category_id is None:
        return projects.order_by('category__order', 'category_id', 'order', '-created_at')
    return projects.filter(category_id=category_id)
