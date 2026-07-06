import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.projects.models import Project

User = get_user_model()


@pytest.mark.django_db
def test_프로젝트_생성() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:project-create'), {
        'category': 'side',
        'title': '테스트 프로젝트',
        'description': '설명',
        'tags': '[]',
        'status': 'in_progress',
        'order': 0,
        'period': '',
        'team_size': '',
        'role': '',
        'highlights': '[]',
        'github_href': '',
        'demo_href': '',
        'title_href': '',
    })

    assert response.status_code == 200
    assert Project.objects.filter(title='테스트 프로젝트').exists()


@pytest.mark.django_db
def test_하이라이트_빈값이면_빈리스트로_저장된다() -> None:
    """highlights 텍스트영역을 빈 값으로 제출해도 IntegrityError 없이 빈 리스트로 저장되어야 한다."""
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:project-create'), {
        'category': 'side',
        'title': '하이라이트 없는 프로젝트',
        'description': '설명',
        'tags': '[]',
        'status': 'in_progress',
        'order': 0,
        'period': '',
        'team_size': '',
        'role': '',
        'highlights': '',
        'github_href': '',
        'demo_href': '',
        'title_href': '',
    })

    assert response.status_code == 200
    project = Project.objects.get(title='하이라이트 없는 프로젝트')
    assert project.highlights == []


@pytest.mark.django_db
def test_필수_필드_누락시_저장되지_않는다() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:project-create'), {'title': ''})

    assert response.status_code == 200
    assert Project.objects.count() == 0


@pytest.mark.django_db
def test_프로젝트_수정() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    project = Project.objects.create(category='side', title='원래 제목', description='d', status='in_progress')
    client = Client()
    client.force_login(owner)

    response = client.post(reverse('dashboard:project-update', args=[project.pk]), {
        'category': 'side',
        'title': '수정된 제목',
        'description': 'd',
        'tags': '[]',
        'status': 'completed',
        'order': 0,
        'period': '',
        'team_size': '',
        'role': '',
        'highlights': '[]',
        'github_href': '',
        'demo_href': '',
        'title_href': '',
    })

    assert response.status_code == 200
    project.refresh_from_db()
    assert project.title == '수정된 제목'
    assert project.status == 'completed'


@pytest.mark.django_db
def test_프로젝트_삭제는_POST만_허용() -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    project = Project.objects.create(category='side', title='삭제 대상', description='d', status='in_progress')
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('dashboard:project-delete', args=[project.pk]))
    assert response.status_code == 405

    response = client.post(reverse('dashboard:project-delete', args=[project.pk]))
    assert response.status_code == 200
    assert not Project.objects.filter(pk=project.pk).exists()


@pytest.mark.django_db
def test_비staff는_프로젝트_생성_불가() -> None:
    reader = User.objects.create_user(username='reader', is_staff=False)
    client = Client()
    client.force_login(reader)

    response = client.get(reverse('dashboard:project-list'))

    assert response.status_code == 403
