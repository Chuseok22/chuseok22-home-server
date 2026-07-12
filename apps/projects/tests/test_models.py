import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import Client
from django.urls import reverse

from apps.projects.models import Project, ProjectCategory, ProjectStatus


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_시딩_마이그레이션으로_초기_카테고리가_order_순서대로_생성되어_있다() -> None:
    names = list(ProjectCategory.objects.values_list('name', flat=True))
    assert names == ['팀 프로젝트', '사이드 프로젝트', '오픈소스']


@pytest.mark.django_db
def test_시딩_마이그레이션으로_초기_상태가_order_순서대로_생성되어_있다() -> None:
    names = list(ProjectStatus.objects.values_list('name', flat=True))
    assert names == ['진행중', '완료', '중단']


@pytest.mark.django_db
def test_ProjectCategory_이름은_유일해야_한다() -> None:
    with pytest.raises(IntegrityError):
        ProjectCategory.objects.create(name='팀 프로젝트', order=99)


@pytest.mark.django_db
def test_ProjectCategory의_문자열_표현은_이름이다() -> None:
    category = ProjectCategory.objects.get(name='팀 프로젝트')
    assert str(category) == '팀 프로젝트'


@pytest.mark.django_db
def test_ProjectStatus_이름은_유일해야_한다() -> None:
    with pytest.raises(IntegrityError):
        ProjectStatus.objects.create(name='진행중', order=99)


@pytest.mark.django_db
def test_ProjectStatus의_문자열_표현은_이름이다() -> None:
    status = ProjectStatus.objects.get(name='진행중')
    assert str(status) == '진행중'


@pytest.mark.django_db
def test_ProjectCategoryAdmin에서_새_카테고리를_추가할_수_있다(admin_client: Client) -> None:
    url = reverse('admin:projects_projectcategory_add')
    response = admin_client.post(url, {'name': '해커톤', 'order': 3, '_save': 'Save'})

    assert response.status_code == 302
    assert ProjectCategory.objects.filter(name='해커톤').exists()


@pytest.mark.django_db
def test_ProjectStatusAdmin에서_새_상태를_추가할_수_있다(admin_client: Client) -> None:
    url = reverse('admin:projects_projectstatus_add')
    response = admin_client.post(url, {'name': '보류', 'order': 3, '_save': 'Save'})

    assert response.status_code == 302
    assert ProjectStatus.objects.filter(name='보류').exists()


@pytest.mark.django_db
def test_참조중인_ProjectCategory는_삭제할_수_없다() -> None:
    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=category, status=status, title='제목', description='설명')

    with pytest.raises(ProtectedError):
        category.delete()


@pytest.mark.django_db
def test_참조중인_ProjectStatus는_삭제할_수_없다() -> None:
    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=category, status=status, title='제목', description='설명')

    with pytest.raises(ProtectedError):
        status.delete()
