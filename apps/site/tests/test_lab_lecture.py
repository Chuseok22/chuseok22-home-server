from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import Course, Lecture
from apps.sejong.lecture.services.ecampus_auth import EcampusSession

User = get_user_model()


def _login_owner(client: Client) -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client.force_login(owner)


@pytest.mark.django_db
def test_비로그인_사용자는_403() -> None:
    client = Client()
    response = client.get(reverse('site:lab-lecture'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_소유자는_강의_페이지_접근_가능() -> None:
    client = Client()
    _login_owner(client)

    response = client.get(reverse('site:lab-lecture'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_로그인_실패시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    with patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=None):
        response = client.get(reverse('site:lab-lecture-courses'))

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '로그인에 실패' in response.content.decode()


@pytest.mark.django_db
def test_강좌_목록_조회() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=fake_courses),
    ):
        response = client.get(reverse('site:lab-lecture-courses'))

    body = response.content.decode()
    assert response.status_code == 200
    assert '자료구조' in body


@pytest.mark.django_db
def test_강좌가_없으면_안내문구_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=[]),
    ):
        response = client.get(reverse('site:lab-lecture-courses'))

    assert response.status_code == 200
    assert '수강 중인 강좌가 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_강좌_선택시_강의_목록_조회() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(reverse('site:lab-lecture-courses'), {'course_id': '101'})

    body = response.content.decode()
    assert response.status_code == 200
    assert '1주차 강의' in body
    assert '자료구조' in body


@pytest.mark.django_db
def test_존재하지_않는_강좌_선택시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=[]),
    ):
        response = client.get(reverse('site:lab-lecture-courses'), {'course_id': '999'})

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_다운로드_요청_성공() -> None:
    """course_name/lecture_title은 더 이상 클라이언트 제출값을 신뢰하지 않고
    서버에서 EcampusCourseService로 다시 조회해 확정한다."""
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]
    fake_job = LectureDownloadJob(
        id=1, course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
    )

    with (
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=fake_job) as mock_start,
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '5001',
        })

    assert response.status_code == 200
    assert '다운로드를 시작' in response.content.decode()
    mock_start.assert_called_once()
    course, lecture = mock_start.call_args.args
    assert course.id == '101' and course.name == '자료구조'
    assert lecture.id == '5001' and lecture.title == '1주차 강의'


@pytest.mark.django_db
def test_존재하지_않는_강좌로_다운로드_요청시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    with patch('apps.site.views.EcampusCourseService.list_courses', return_value=[]):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '999', 'lecture_id': '5001',
        })

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_강좌에_속하지_않는_강의로_다운로드_요청시_200으로_에러메시지_반환() -> None:
    """course_id는 실재하지만 lecture_id가 그 강좌에 속하지 않는 조작된 조합 - 다른
    강좌의 메타데이터로 엉뚱한 강의가 다운로드되는 것을 서버 측 재검증으로 막는다."""
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조')]

    with (
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=[]),
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '9999',
        })

    assert response.status_code == 200
    assert '강의를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_이미_진행중인_작업이_있으면_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusCourseService.list_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=None),
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '5001',
        })

    assert response.status_code == 200
    assert '이미 진행 중' in response.content.decode()


@pytest.mark.django_db
def test_다운로드_요청_필수값_누락시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    response = client.post(reverse('site:lab-lecture-download'), {'course_id': '101'})

    assert response.status_code == 200
    assert '올바르지 않습니다' in response.content.decode()


@pytest.mark.django_db
def test_이력_목록_조회() -> None:
    client = Client()
    _login_owner(client)
    LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.COMPLETED,
    )

    response = client.get(reverse('site:lab-lecture-history'))

    assert response.status_code == 200
    assert '1주차 강의' in response.content.decode()


@pytest.mark.django_db
def test_이력이_없으면_안내문구_반환() -> None:
    client = Client()
    _login_owner(client)

    response = client.get(reverse('site:lab-lecture-history'))

    assert response.status_code == 200
    assert '다운로드 이력이 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_이력_삭제() -> None:
    client = Client()
    _login_owner(client)
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.FAILED,
    )

    response = client.post(reverse('site:lab-lecture-history-delete', args=[job.id]))

    assert response.status_code == 200
    assert not LectureDownloadJob.objects.filter(pk=job.id).exists()


@pytest.mark.django_db
def test_진행중인_작업_삭제요청은_409() -> None:
    """진행 중(PENDING/RUNNING)인 작업은 삭제할 수 없다 - 오케스트레이터의 동시 실행
    제한이 job 행 존재 여부로 동작하므로, 삭제를 허용하면 그 제한이 무력화된다."""
    client = Client()
    _login_owner(client)
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.RUNNING,
    )

    response = client.post(reverse('site:lab-lecture-history-delete', args=[job.id]))

    assert response.status_code == 409
    assert LectureDownloadJob.objects.filter(pk=job.id).exists()


@pytest.mark.django_db
def test_존재하지_않는_이력_삭제요청도_200() -> None:
    client = Client()
    _login_owner(client)

    response = client.post(reverse('site:lab-lecture-history-delete', args=[999999]))

    assert response.status_code == 200


@pytest.mark.django_db
def test_완료되지_않은_작업의_파일_다운로드는_404() -> None:
    client = Client()
    _login_owner(client)
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.RUNNING,
    )

    response = client.get(reverse('site:lab-lecture-history-file', args=[job.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_완료된_작업의_파일이_디스크에_없으면_404(tmp_path) -> None:
    client = Client()
    _login_owner(client)
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.COMPLETED, file_relative_path='missing.mp4',
    )

    with override_settings(MEDIA_ROOT=str(tmp_path / 'media')):
        response = client.get(reverse('site:lab-lecture-history-file', args=[job.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_완료된_작업의_파일_다운로드_성공(tmp_path) -> None:
    lectures_root = tmp_path / 'lectures'
    lectures_root.mkdir()
    (lectures_root / '1.mp4').write_bytes(b'fake-mp4-content')

    client = Client()
    _login_owner(client)
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.COMPLETED, file_relative_path='1.mp4',
    )

    with override_settings(MEDIA_ROOT=str(tmp_path / 'media')):
        response = client.get(reverse('site:lab-lecture-history-file', args=[job.id]))

    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'fake-mp4-content'
