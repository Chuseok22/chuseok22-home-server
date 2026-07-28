import pytest

from apps.projects.models import Project, ProjectCategory, ProjectStatus
from apps.projects.services.category import (
    filter_projects_by_category_id,
    get_project_category_sidebar_items,
)


@pytest.mark.django_db
def test_get_project_category_sidebar_items는_프로젝트가_있는_카테고리만_반환한다() -> None:
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='테스트 프로젝트', description='설명', status=status)

    items = get_project_category_sidebar_items()

    names = [item.name for item in items]
    assert '사이드 프로젝트' in names
    assert '팀 프로젝트' not in names
    assert '오픈소스' not in names


@pytest.mark.django_db
def test_get_project_category_sidebar_items는_order_순으로_반환한다() -> None:
    team = ProjectCategory.objects.get(name='팀 프로젝트')
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드 A', description='설명', status=status)
    Project.objects.create(category=team, title='팀 A', description='설명', status=status)

    items = get_project_category_sidebar_items()

    assert [item.name for item in items] == ['팀 프로젝트', '사이드 프로젝트']


@pytest.mark.django_db
def test_get_project_category_sidebar_items는_order가_같으면_id_순으로_반환한다() -> None:
    # Admin에서 두 카테고리에 같은 order 값을 넣을 수 있으므로, id를 2차 정렬 기준으로
    # 써서 순서가 안정적인지 확인한다.
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    duplicate_order = ProjectCategory.objects.create(name='기타', order=side.order)
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드', description='설명', status=status)
    Project.objects.create(category=duplicate_order, title='기타 프로젝트', description='설명', status=status)

    items = get_project_category_sidebar_items()

    ordered_names = [item.name for item in items if item.name in ('사이드 프로젝트', '기타')]
    assert ordered_names == ['사이드 프로젝트', '기타']


@pytest.mark.django_db
def test_get_project_category_sidebar_items는_각_카테고리의_프로젝트_수를_센다() -> None:
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='A', description='설명', status=status)
    Project.objects.create(category=side, title='B', description='설명', status=status)

    items = get_project_category_sidebar_items()

    side_item = next(item for item in items if item.name == '사이드 프로젝트')
    assert side_item.project_count == 2


@pytest.mark.django_db
def test_filter_projects_by_category_id는_None이면_전체를_반환한다() -> None:
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    team = ProjectCategory.objects.get(name='팀 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드', description='설명', status=status)
    Project.objects.create(category=team, title='팀', description='설명', status=status)

    result = filter_projects_by_category_id(None)

    assert result.count() == 2


@pytest.mark.django_db
def test_filter_projects_by_category_id는_해당_카테고리만_반환한다() -> None:
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    team = ProjectCategory.objects.get(name='팀 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드', description='설명', status=status)
    Project.objects.create(category=team, title='팀', description='설명', status=status)

    result = filter_projects_by_category_id(side.id)

    titles = [p.title for p in result]
    assert titles == ['사이드']


@pytest.mark.django_db
def test_filter_projects_by_category_id는_존재하지_않는_id면_빈_결과를_반환한다() -> None:
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드', description='설명', status=status)

    result = filter_projects_by_category_id(999999)

    assert result.count() == 0
