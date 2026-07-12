import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.projects.models import Project


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_태그와_하이라이트가_빈값이어도_저장된다(admin_client: Client) -> None:
    url = reverse('admin:projects_project_add')
    response = admin_client.post(url, {
        'category': 'side',
        'title': '테스트 프로젝트',
        'description': '설명',
        'tags': '',
        'status': 'in_progress',
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
