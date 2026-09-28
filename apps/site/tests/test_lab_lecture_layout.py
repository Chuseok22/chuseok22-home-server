from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import Course
from apps.sejong.lecture.services.ecampus_auth import EcampusSession

User = get_user_model()


def _login_owner(client: Client) -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client.force_login(owner)


def _create_job(status: str, lecture_title: str = '1주차 강의') -> LectureDownloadJob:
    return LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조 (000001-001)', lecture_id='5001',
        lecture_title=lecture_title, status=status,
    )


@pytest.mark.django_db
def test_이력이_있으면_카드_목록과_표가_모두_렌더링되고_카드는_lg_미만에서만_보인다() -> None:
    client = Client()
    _login_owner(client)
    _create_job(LectureDownloadJob.Status.COMPLETED)

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert 'class="lg:hidden flex flex-col gap-3"' in body
    assert 'class="hidden lg:block overflow-x-auto"' in body
    assert body.count('<tr id="job-row-') == 1


@pytest.mark.django_db
def test_이력_카드에는_강의명_강좌명_상태가_표시된다() -> None:
    client = Client()
    _login_owner(client)
    _create_job(LectureDownloadJob.Status.COMPLETED, lecture_title='카드에서 보이는 강의')

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    # 카드와 표에 각각 한 번씩
    assert body.count('카드에서 보이는 강의') >= 2
    assert body.count('자료구조 (000001-001)') >= 2
    assert body.count('badge badge-success') == 2


@pytest.mark.django_db
def test_완료된_작업은_카드와_표_모두에_다운로드_링크와_삭제_버튼이_있다() -> None:
    client = Client()
    _login_owner(client)
    job = _create_job(LectureDownloadJob.Status.COMPLETED)

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert body.count(reverse('site:lab-lecture-history-file', args=[job.id])) == 2
    assert body.count(reverse('site:lab-lecture-history-delete', args=[job.id])) == 2


@pytest.mark.django_db
def test_진행중인_작업은_카드와_표_어디에도_삭제_버튼이_없다() -> None:
    client = Client()
    _login_owner(client)
    job = _create_job(LectureDownloadJob.Status.RUNNING)

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert body.count('badge badge-info') == 2
    assert reverse('site:lab-lecture-history-delete', args=[job.id]) not in body


@pytest.mark.django_db
def test_이력_표의_상태_열과_버튼_열은_줄바꿈되지_않는다() -> None:
    """768px 부근에서 상태 배지가 세로로 눌리던 결함 방지."""
    client = Client()
    _login_owner(client)
    _create_job(LectureDownloadJob.Status.COMPLETED)

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert '<td class="whitespace-nowrap">' in body
    assert 'class="flex gap-2 justify-end whitespace-nowrap"' in body


@pytest.mark.django_db
def test_교과_강좌_버튼은_강좌명이_길어도_높이가_고정되지_않고_왼쪽_정렬이다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='아주 긴 이름의 교과 강좌 ' * 4, year='2026', semester='20')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
    ):
        response = client.get(reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'})

    assert 'btn btn-ghost justify-start relative h-auto min-h-12 py-2 text-left' in response.content.decode()


def _create_job_in_course(
    course_id: str, course_name: str, lecture_id: str,
    status: str = LectureDownloadJob.Status.COMPLETED,
) -> LectureDownloadJob:
    return LectureDownloadJob.objects.create(
        course_id=course_id, course_name=course_name, lecture_id=lecture_id,
        lecture_title=f'{course_name} {lecture_id}강', status=status,
    )


@pytest.mark.django_db
def test_이력이_있으면_강좌_필터_드롭다운이_한번만_렌더링된다() -> None:
    client = Client()
    _login_owner(client)
    _create_job_in_course('101', '자료구조', '1')
    _create_job_in_course('202', '알고리즘', '2')

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    # 카드/표 두 레이아웃과 무관하게 드롭다운은 목록 위 공통 영역에 하나만 있다.
    assert body.count('id="history-course-filter"') == 1
    assert 'name="course"' in body
    assert f'hx-get="{reverse("site:lab-lecture-history")}"' in body
    assert '<option value="" selected>전체</option>' in body
    assert '<option value="101">자료구조</option>' in body
    assert '<option value="202">알고리즘</option>' in body


@pytest.mark.django_db
def test_선택한_강좌가_드롭다운에서_selected로_표시된다() -> None:
    client = Client()
    _login_owner(client)
    _create_job_in_course('101', '자료구조', '1')
    _create_job_in_course('202', '알고리즘', '2')

    body = client.get(reverse('site:lab-lecture-history'), {'course': '202'}).content.decode()

    assert '<option value="202" selected>알고리즘</option>' in body
    assert '<option value="101">자료구조</option>' in body
    assert '<option value="" selected>전체</option>' not in body
    assert body.count('<tr id="job-row-') == 1


@pytest.mark.django_db
def test_이력이_하나도_없으면_드롭다운_없이_빈_상태_문구만_보인다() -> None:
    client = Client()
    _login_owner(client)

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert 'history-course-filter' not in body
    assert '다운로드 이력이 없습니다' in body


@pytest.mark.django_db
def test_강좌_필터_상태의_이전_다음_링크는_course를_함께_전달한다() -> None:
    client = Client()
    _login_owner(client)
    for i in range(45):
        _create_job_in_course('101', '자료구조', str(i))
    _create_job_in_course('202', '알고리즘', 'a')

    body = client.get(reverse('site:lab-lecture-history'), {'course': '101', 'page': '2'}).content.decode()

    # 이전/다음 링크 각각 href와 hx-get 두 곳에 들어간다.
    assert body.count('?page=1&course=101') == 2
    assert body.count('?page=3&course=101') == 2


@pytest.mark.django_db
def test_강좌_필터가_없으면_링크에_course_파라미터가_붙지_않는다() -> None:
    client = Client()
    _login_owner(client)
    for i in range(25):
        _create_job_in_course('101', '자료구조', str(i))

    body = client.get(reverse('site:lab-lecture-history')).content.decode()

    assert '?page=2"' in body
    assert '&course=' not in body


@pytest.mark.django_db
def test_삭제_버튼_URL은_선택된_강좌를_함께_전달한다() -> None:
    client = Client()
    _login_owner(client)
    job = _create_job_in_course('101', '자료구조', '1')
    _create_job_in_course('202', '알고리즘', '2')
    delete_url = reverse('site:lab-lecture-history-delete', args=[job.id])

    filtered_body = client.get(reverse('site:lab-lecture-history'), {'course': '101'}).content.decode()
    unfiltered_body = client.get(reverse('site:lab-lecture-history')).content.decode()

    # 카드와 표에 각각 한 번씩
    assert filtered_body.count(f'{delete_url}?page=1&course=101"') == 2
    assert f'{delete_url}?page=1"' in unfiltered_body
    assert '&course=' not in unfiltered_body
