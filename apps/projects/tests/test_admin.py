import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.projects.models import Project, ProjectCategory, ProjectStatus
from apps.projects.admin import NewlineSeparatedListField


def test_NewlineSeparatedListField_줄바꿈_텍스트를_리스트로_변환한다() -> None:
    field = NewlineSeparatedListField(required=False)
    assert field.clean('Java\nSpring Boot\nPostgreSQL') == ['Java', 'Spring Boot', 'PostgreSQL']


def test_NewlineSeparatedListField_불릿_기호를_제거한다() -> None:
    field = NewlineSeparatedListField(required=False)
    assert field.clean('• 항목1\n- 항목2\n* 항목3') == ['항목1', '항목2', '항목3']


def test_NewlineSeparatedListField_공백_없는_하이픈_별표는_내용으로_보존한다() -> None:
    # '-'/'*'는 뒤에 공백이 있을 때만 불릿으로 간주한다. 공백이 없으면
    # '-Xmx512m', '*args'처럼 실제 값의 일부일 수 있으므로 그대로 보존한다.
    field = NewlineSeparatedListField(required=False)
    assert field.clean('-Xmx512m\n*args') == ['-Xmx512m', '*args']


def test_NewlineSeparatedListField_빈_줄은_무시한다() -> None:
    field = NewlineSeparatedListField(required=False)
    assert field.clean('Java\n\n\nSpring Boot') == ['Java', 'Spring Boot']


def test_NewlineSeparatedListField_빈_입력은_빈_리스트를_반환한다() -> None:
    field = NewlineSeparatedListField(required=False)
    assert field.clean('') == []
    assert field.clean(None) == []


def test_NewlineSeparatedListField_저장된_리스트를_줄바꿈_텍스트로_되돌린다() -> None:
    field = NewlineSeparatedListField(required=False)
    assert field.prepare_value(['Java', 'Spring Boot']) == 'Java\nSpring Boot'
    assert field.prepare_value([]) == ''


def test_NewlineSeparatedListField_리스트에_문자열이_아닌_값이_있어도_텍스트로_변환한다() -> None:
    # 과거 raw JSON 위젯으로 [2024]처럼 문자열이 아닌 값이 저장돼 있을 수 있으므로,
    # prepare_value가 이런 값에서도 예외 없이 텍스트로 변환되는지 확인한다.
    field = NewlineSeparatedListField(required=False)
    assert field.prepare_value([2024, 'Java']) == '2024\nJava'


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_태그와_하이라이트가_빈값이어도_저장된다(admin_client: Client) -> None:
    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    url = reverse('admin:projects_project_add')
    response = admin_client.post(url, {
        'category': category.pk,
        'title': '테스트 프로젝트',
        'description': '설명',
        'tags': '',
        'status': status.pk,
        'order': 0,
        'period': '',
        'team_size': '',
        'role': '',
        'highlights': '',
        'github_href': '',
        'demo_href': '',
        'title_href': '',
        '_save': 'Save',
    })

    assert response.status_code == 302
    project = Project.objects.get(title='테스트 프로젝트')
    assert project.tags == []
    assert project.highlights == []
