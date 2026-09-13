from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.http import content_disposition_header

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import Course, Lecture
from apps.sejong.lecture.services.ecampus_auth import EcampusSession
from apps.sejong.lecture.services.filename import build_lecture_filename

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
    body = response.content.decode()

    assert response.status_code == 200
    # 연도/학기 select가 좁게 렌더링되어 텍스트가 잘리는 버그(GitHub 이슈 #164) 방지
    assert 'id="course-year" name="year" class="select select-bordered select-sm min-w-32"' in body
    assert 'id="course-semester" name="semester" class="select select-bordered select-sm min-w-32"' in body


@pytest.mark.django_db
def test_로그인_실패시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    with patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=None):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'},
        )

    assert response.status_code == 200  # htmx가 swap하려면 2xx여야 함
    assert '로그인에 실패' in response.content.decode()


@pytest.mark.django_db
def test_강좌_조회_결과_표시() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert '자료구조' in body


@pytest.mark.django_db
def test_강좌_조회_응답은_이전_다운로드결과를_비운다() -> None:
    """학기를 바꿔 다시 조회했을 때 이전에 표시됐던 다운로드 결과 메시지(#download-result)가
    화면에 남아있지 않도록, 강좌 조회(course_id 없는 요청) 응답은 이 영역을 htmx
    out-of-band swap으로 비운다. 강좌를 클릭해 강의 목록을 펼치는 요청(course_id 있음)에서는
    비우지 않는다 - 직전 다운로드 상태 메시지를 유지해야 하기 때문이다."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert 'id="download-result" hx-swap-oob' in body


@pytest.mark.django_db
def test_강좌가_없으면_안내문구_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=[]),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'},
        )

    assert response.status_code == 200
    assert '해당 학기에 강좌가 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_강좌_선택시_강의_목록_조회() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '101', 'year': '2026', 'semester': '20'},
        )

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
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=[]),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '999', 'year': '2026', 'semester': '20'},
        )

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_강좌_조회_잘못된_연도_학기_값은_거부() -> None:
    client = Client()
    _login_owner(client)

    response = client.get(
        reverse('site:lab-lecture-courses'), {'year': '1999', 'semester': '1학기'},
    )

    assert response.status_code == 200
    assert '올바르지 않습니다' in response.content.decode()


@pytest.mark.django_db
def test_다운로드_요청_성공() -> None:
    """course_name/lecture_title은 더 이상 클라이언트 제출값을 신뢰하지 않고
    서버에서 EcampusCourseService로 다시 조회해 확정한다."""
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]
    fake_job = LectureDownloadJob(
        id=1, course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
    )

    with (
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=fake_job) as mock_start,
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '5001', 'year': '2026', 'semester': '20',
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

    with patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=[]):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '999', 'lecture_id': '5001', 'year': '2026', 'semester': '20',
        })

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_강좌에_속하지_않는_강의로_다운로드_요청시_200으로_에러메시지_반환() -> None:
    """course_id는 실재하지만 lecture_id가 그 강좌에 속하지 않는 조작된 조합 - 다른
    강좌의 메타데이터로 엉뚱한 강의가 다운로드되는 것을 서버 측 재검증으로 막는다."""
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]

    with (
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=[]),
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '9999', 'year': '2026', 'semester': '20',
        })

    assert response.status_code == 200
    assert '강의를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_이미_진행중인_작업이_있으면_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=None),
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '101', 'lecture_id': '5001', 'year': '2026', 'semester': '20',
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
def test_다운로드_요청_잘못된_연도_학기_값은_거부() -> None:
    client = Client()
    _login_owner(client)

    response = client.post(reverse('site:lab-lecture-download'), {
        'course_id': '101', 'lecture_id': '5001', 'year': '1999', 'semester': '1학기',
    })

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


@pytest.mark.django_db
def test_특정_연도_학기_지정시_해당_학기만_검색() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_past_courses = [Course(id='201', name='이산수학', year='2023', semester='10')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_past_courses',
            return_value=fake_past_courses,
        ) as mock_search,
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2023', 'semester': '10'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert '이산수학' in body
    mock_search.assert_called_once_with(year='2023', semester='10')


@pytest.mark.django_db
def test_전체_조회시_아코디언_마크업_렌더링() -> None:
    """year/semester를 'all'로 조회해 결과가 서로 다른 학기에 걸쳐 있으면 그룹 헤더(아코디언)와
    함께 렌더링돼야 한다 - 이 분기는 기존 테스트가 전혀 실행하지 않던 경로다."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [
        Course(id='301', name='최신강좌', year='2026', semester='20'),
        Course(id='201', name='이산수학', year='2023', semester='10'),
    ]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_past_courses',
            return_value=fake_courses,
        ),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': 'all', 'semester': 'all'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert 'collapse-arrow' in body
    assert '2026년 2학기' in body
    assert '2023년 1학기' in body


@pytest.mark.django_db
def test_특정_학기_조회시_아코디언_마크업_없음() -> None:
    """특정 연도+특정 학기를 명시적으로 조회하면 그룹이 하나로 접혀 아코디언 없이
    평평한 목록으로만 렌더링돼야 한다."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [
        Course(id='101', name='자료구조', year='2026', semester='20'),
        Course(id='102', name='운영체제', year='2026', semester='20'),
    ]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_past_courses',
            return_value=fake_courses,
        ),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': '2026', 'semester': '20'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert 'collapse-arrow' not in body


@pytest.mark.django_db
def test_강좌_선택시_해당_학기에서_재검증() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_past_courses = [Course(id='201', name='이산수학', year='2023', semester='10')]
    fake_lectures = [Lecture(id='7001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_past_courses',
            return_value=fake_past_courses,
        ) as mock_search,
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '201', 'year': '2023', 'semester': '10'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert '1주차 강의' in body
    mock_search.assert_called_once_with(year='2023', semester='10')


@pytest.mark.django_db
def test_강좌를_클릭하면_해당_강좌만_인라인으로_펼쳐진다() -> None:
    """course_id로 조회하면 그 강좌의 강의 목록만 강좌 목록 안에 함께 렌더링되고, 전역
    #lectures 영역은 더 이상 렌더링되지 않는다(인라인 확장으로 구조가 바뀌었다)."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [
        Course(id='101', name='자료구조', year='2026', semester='20'),
        Course(id='102', name='운영체제', year='2026', semester='20'),
    ]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures) as mock_list,
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '101', 'year': '2026', 'semester': '20'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert '자료구조' in body
    assert '운영체제' in body
    assert '1주차 강의' in body
    mock_list.assert_called_once_with('101')
    assert '<div id="lectures"' not in body


@pytest.mark.django_db
def test_펼쳐진_강좌가_속한_학기_그룹은_첫번째가_아니어도_열려있다() -> None:
    """강좌 조회 결과가 여러 학기 그룹으로 나뉠 때, 인라인으로 펼쳐진 강좌가 첫 번째가
    아닌 다른 그룹에 속해도 그 그룹의 아코디언이 열려 있어야 한다(학기 그룹 체크박스는
    서로 독립적이라 여러 개가 동시에 열려도 된다)."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [
        Course(id='301', name='최신강좌', year='2026', semester='20'),
        Course(id='201', name='이산수학', year='2023', semester='10'),
    ]
    fake_lectures = [Lecture(id='7001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '201', 'year': 'all', 'semester': 'all'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    # 최신강좌가 속한 첫 번째 그룹(2026년 2학기, forloop.first)과, 인라인으로 펼쳐진
    # 이산수학이 속한 두 번째 그룹(2023년 1학기) 둘 다 checked여야 한다.
    assert body.count('checked') == 2


@pytest.mark.django_db
def test_강좌_버튼과_다운로드_버튼의_로딩_스피너는_절대위치로_렌더링된다() -> None:
    """숨겨진 스피너가 flex 레이아웃 공간을 차지해 텍스트가 버튼 중앙에서 벗어나 보이는
    버그(GitHub 이슈 #164)를 막기 위해 스피너를 absolute로 배치했는지 검증한다."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조', year='2026', semester='20')]
    fake_lectures = [Lecture(id='5001', title='1주차 강의')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'),
            {'course_id': '101', 'year': '2026', 'semester': '20'},
        )

    body = response.content.decode()
    # 강좌 버튼(인라인 로딩 스피너) + 다운로드 버튼(기존 버그 대상) 둘 다 absolute 배치.
    assert body.count('loading-spinner loading-xs absolute right-2') == 2


@pytest.mark.django_db
def test_전체_조회중_강좌_클릭시_버튼은_검색_필터_학기로_재조회한다() -> None:
    """강좌 버튼의 hx-vals가 그 강좌 자신의 학기(course.year/course.semester)가 아니라
    이 목록을 조회할 때 쓴 필터(year='all'/semester='all')를 실어 보내야 한다 - 그렇지 않으면
    강좌를 클릭했을 때 그 강좌의 실제 학기만으로 재조회되어 group_courses_by_semester가 단일
    그룹만 반환하고, 지금 보고 있던 다른 학기의 강좌들이 화면에서 전부 사라진다
    (fable5.1 계획 리뷰로 발견 - GitHub 이슈 #164)."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [Course(id='101', name='자료구조', year='2023', semester='10')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_past_courses', return_value=fake_courses),
    ):
        response = client.get(
            reverse('site:lab-lecture-courses'), {'year': 'all', 'semester': 'all'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert '"course_id": "101", "year": "all", "semester": "all"' in body


@pytest.mark.django_db
def test_다운로드_요청시_해당_학기에서_재검증() -> None:
    client = Client()
    _login_owner(client)
    fake_past_courses = [Course(id='201', name='이산수학', year='2023', semester='10')]
    fake_lectures = [Lecture(id='7001', title='1주차 강의')]
    fake_job = LectureDownloadJob(
        id=1, course_id='201', course_name='이산수학', lecture_id='7001', lecture_title='1주차 강의',
    )

    with (
        patch(
            'apps.site.views.EcampusCourseService.search_past_courses',
            return_value=fake_past_courses,
        ) as mock_search,
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=fake_job) as mock_start,
    ):
        response = client.post(reverse('site:lab-lecture-download'), {
            'course_id': '201', 'lecture_id': '7001', 'year': '2023', 'semester': '10',
        })

    assert response.status_code == 200
    assert '다운로드를 시작' in response.content.decode()
    mock_search.assert_called_once_with(year='2023', semester='10')
    mock_start.assert_called_once()


@pytest.mark.django_db
def test_완료된_강의_다운로드_파일명에_강좌명이_포함된다(tmp_path) -> None:
    client = Client()
    _login_owner(client)

    with override_settings(MEDIA_ROOT=tmp_path / 'output' / 'media'):
        job = LectureDownloadJob.objects.create(
            course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
            status=LectureDownloadJob.Status.COMPLETED,
            file_relative_path='1.mp4',
        )
        file_path = job.storage_root / job.file_relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b'fake video content')

        response = client.get(
            reverse('site:lab-lecture-history-file', kwargs={'job_id': job.id}),
        )

    expected_filename = build_lecture_filename(job.course_name, job.lecture_title)
    assert response.status_code == 200
    assert response['Content-Disposition'] == content_disposition_header(True, expected_filename)
