from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import IrregularCourse, Lecture
from apps.sejong.lecture.services.ecampus_auth import EcampusSession

User = get_user_model()


def _login_owner(client: Client) -> None:
    owner = User.objects.create_user(username='owner', is_staff=True)
    client.force_login(owner)


@pytest.mark.django_db
def test_비교과_강좌_조회는_비로그인_사용자에게_403() -> None:
    response = Client().get(reverse('site:lab-lecture-irregular-courses'), {'year': '2026'})

    assert response.status_code == 403


@pytest.mark.django_db
def test_비교과_다운로드는_비로그인_사용자에게_403() -> None:
    response = Client().post(reverse('site:lab-lecture-irregular-download'), {
        'course_id': '34888', 'lecture_id': '5001', 'year': '2026',
    })

    assert response.status_code == 403


@pytest.mark.django_db
def test_비교과_강좌_조회_로그인_실패시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    with patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=None):
        response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': '2026'})

    assert response.status_code == 200
    assert '로그인에 실패' in response.content.decode()


@pytest.mark.django_db
def test_비교과_강좌_조회_결과에_연도와_강좌명이_표시된다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [
        IrregularCourse(id='34888', name='PBL 학생 OT', year='2026'),
        IrregularCourse(id='11800', name='FL 학생 OT', year='2024'),
    ]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ) as mock_search,
    ):
        response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': 'all'})

    body = response.content.decode()
    assert response.status_code == 200
    assert 'PBL 학생 OT' in body and 'FL 학생 OT' in body
    assert '2026' in body and '2024' in body
    mock_search.assert_called_once_with(year='all')


@pytest.mark.django_db
def test_비교과_강좌_조회_응답은_이전_다운로드결과를_비운다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ),
    ):
        response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': '2026'})

    assert 'id="irregular-download-result" hx-swap-oob' in response.content.decode()


@pytest.mark.django_db
def test_비교과_강좌가_없으면_안내문구_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_irregular_courses', return_value=[]),
    ):
        response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': '2025'})

    assert response.status_code == 200
    assert '해당 연도에 비교과 강좌가 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_강좌_선택시_강의_목록이_인라인으로_펼쳐진다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')]
    fake_lectures = [Lecture(id='5001', title='OT 영상')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-irregular-courses'),
            {'course_id': '34888', 'year': '2026'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    assert 'OT 영상' in body
    assert reverse('site:lab-lecture-irregular-download') in body
    # 다운로드 폼의 숨은 year는 강좌 자신의 연도다
    assert 'name="year" value="2026"' in body
    # 강좌를 펼치는 요청에서는 직전 다운로드 결과 영역을 비우지 않는다
    assert 'id="irregular-download-result" hx-swap-oob' not in body


@pytest.mark.django_db
def test_비교과_강좌_버튼_재조회는_검색_연도를_쓰고_다운로드_폼은_강좌_연도를_쓴다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [IrregularCourse(id='11800', name='FL 학생 OT', year='2024')]
    fake_lectures = [Lecture(id='5001', title='OT 영상')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
    ):
        response = client.get(
            reverse('site:lab-lecture-irregular-courses'),
            {'course_id': '11800', 'year': 'all'},
        )

    body = response.content.decode()
    assert response.status_code == 200
    # 버튼의 hx-vals는 검색 연도를 유지해 다른 연도 강좌도 계속 목록에 남긴다
    assert '"year": "all"' in body
    # 다운로드 폼은 강좌 자신의 연도를 쓴다
    assert 'name="year" value="2024"' in body


@pytest.mark.django_db
def test_비교과_강의가_없는_강좌를_선택하면_안내문구가_표시된다() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=[]),
    ):
        response = client.get(
            reverse('site:lab-lecture-irregular-courses'),
            {'course_id': '34888', 'year': '2026'},
        )

    assert '다운로드 가능한 영상이 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_존재하지_않는_비교과_강좌_선택시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch('apps.site.views.EcampusCourseService.search_irregular_courses', return_value=[]),
    ):
        response = client.get(
            reverse('site:lab-lecture-irregular-courses'),
            {'course_id': '999', 'year': '2026'},
        )

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_강좌_조회_잘못된_연도는_거부() -> None:
    client = Client()
    _login_owner(client)

    response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': '1999'})

    assert response.status_code == 200
    assert '올바르지 않습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_다운로드_요청_성공() -> None:
    client = Client()
    _login_owner(client)
    fake_course = IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')
    fake_lectures = [Lecture(id='5001', title='OT 영상')]
    fake_job = LectureDownloadJob(
        id=1, course_id='34888', course_name='PBL 학생 OT', lecture_id='5001', lecture_title='OT 영상',
    )

    with (
        patch(
            'apps.site.views.EcampusCourseService.find_irregular_course',
            return_value=fake_course,
        ) as mock_find,
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch(
            'apps.site.views.LectureDownloadOrchestrator.start', return_value=fake_job,
        ) as mock_start,
    ):
        response = client.post(reverse('site:lab-lecture-irregular-download'), {
            'course_id': '34888', 'lecture_id': '5001', 'year': '2026',
        })

    assert response.status_code == 200
    assert '다운로드를 시작' in response.content.decode()
    mock_find.assert_called_once_with('34888', year='2026')
    mock_start.assert_called_once()
    course, lecture = mock_start.call_args.args
    assert isinstance(course, IrregularCourse) and course.id == '34888'
    assert lecture.id == '5001' and lecture.title == 'OT 영상'


@pytest.mark.django_db
def test_존재하지_않는_비교과_강좌로_다운로드_요청시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    with patch('apps.site.views.EcampusCourseService.find_irregular_course', return_value=None):
        response = client.post(reverse('site:lab-lecture-irregular-download'), {
            'course_id': '999', 'lecture_id': '5001', 'year': '2026',
        })

    assert response.status_code == 200
    assert '강좌를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_강좌에_속하지_않는_강의로_다운로드_요청시_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_course = IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')

    with (
        patch(
            'apps.site.views.EcampusCourseService.find_irregular_course',
            return_value=fake_course,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=[]),
    ):
        response = client.post(reverse('site:lab-lecture-irregular-download'), {
            'course_id': '34888', 'lecture_id': '9999', 'year': '2026',
        })

    assert response.status_code == 200
    assert '강의를 찾을 수 없습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_다운로드_이미_진행중인_작업이_있으면_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)
    fake_course = IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')
    fake_lectures = [Lecture(id='5001', title='OT 영상')]

    with (
        patch(
            'apps.site.views.EcampusCourseService.find_irregular_course',
            return_value=fake_course,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=None),
    ):
        response = client.post(reverse('site:lab-lecture-irregular-download'), {
            'course_id': '34888', 'lecture_id': '5001', 'year': '2026',
        })

    assert response.status_code == 200
    assert '이미 진행 중인 다운로드 작업이 있습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_다운로드_잘못된_입력은_200으로_에러메시지_반환() -> None:
    client = Client()
    _login_owner(client)

    response = client.post(reverse('site:lab-lecture-irregular-download'), {
        'course_id': '34888', 'year': '2026',
    })

    assert response.status_code == 200
    assert '입력값이 올바르지 않습니다' in response.content.decode()


@pytest.mark.django_db
def test_비교과_다운로드는_GET_요청을_405로_거부한다() -> None:
    client = Client()
    _login_owner(client)

    response = client.get(reverse('site:lab-lecture-irregular-download'))

    assert response.status_code == 405


@pytest.mark.django_db
def test_강의_페이지에_교과_비교과_탭이_있고_비교과_조회_폼이_연결된다() -> None:
    client = Client()
    _login_owner(client)

    body = client.get(reverse('site:lab-lecture')).content.decode()

    assert 'x-data="{ tab: \'regular\' }"' in body
    assert 'id="regular-tab"' in body and '>교과</button>' in body
    assert 'id="irregular-tab"' in body and '>비교과</button>' in body
    assert f'hx-get="{reverse("site:lab-lecture-irregular-courses")}"' in body
    # 비교과 탭은 처음 선택(클릭)할 때만 자동 조회한다
    assert 'hx-trigger="submit, click from:#irregular-tab once"' in body
    assert 'id="irregular-year" name="year" class="select select-bordered select-sm min-w-32"' in body
    assert 'id="irregular-courses"' in body
    assert 'id="irregular-courses-skeleton"' in body
    assert 'id="irregular-download-result"' in body
    # 비교과는 학기 select가 없다
    assert body.count('name="semester"') == 1


@pytest.mark.django_db
def test_강의_페이지의_교과_탭_기존_요소는_유지된다() -> None:
    client = Client()
    _login_owner(client)

    body = client.get(reverse('site:lab-lecture')).content.decode()

    assert 'id="course-year" name="year"' in body
    assert 'id="course-semester" name="semester"' in body
    assert 'id="courses"' in body
    assert 'id="courses-skeleton"' in body
    assert 'id="download-result"' in body


@pytest.mark.django_db
def test_강의_페이지_탭은_알약형이고_라벨은_줄바꿈되지_않는다() -> None:
    """DaisyUI tabs-lifted(라디오+tab-content)는 그리드 레이아웃에 의존해, flex로 덮어쓰면 패널이
    397px로 좁아지고 탭이 패널 아래로 밀리는 회귀가 있었다. 버튼 기반 tabs-boxed로 교체했다."""
    client = Client()
    _login_owner(client)

    body = client.get(reverse('site:lab-lecture')).content.decode()

    assert 'role="tablist" class="tabs tabs-boxed w-fit mb-4"' in body
    assert 'tabs-lifted' not in body
    assert 'tab-content' not in body
    assert body.count('class="tab whitespace-nowrap"') == 2


@pytest.mark.django_db
def test_비교과_강좌_버튼은_강좌명이_길어도_높이가_고정되지_않는다() -> None:
    """DaisyUI `.btn`의 고정 높이(3rem) 때문에 두 줄로 넘어가는 강좌명이 다음 항목과 겹치던 결함 방지."""
    client = Client()
    _login_owner(client)
    fake_session = EcampusSession(session=MagicMock())
    fake_courses = [IrregularCourse(id='34888', name='아주 긴 이름의 비교과 강좌 ' * 4, year='2026')]

    with (
        patch('apps.site.views.EcampusMoodleAuthService.create_session', return_value=fake_session),
        patch(
            'apps.site.views.EcampusCourseService.search_irregular_courses',
            return_value=fake_courses,
        ),
    ):
        response = client.get(reverse('site:lab-lecture-irregular-courses'), {'year': '2026'})

    assert 'btn btn-ghost justify-start relative h-auto min-h-12 py-2 text-left' in response.content.decode()


@pytest.mark.django_db
def test_비교과_다운로드_응답의_강의_제목은_HTML_이스케이프된다() -> None:
    client = Client()
    _login_owner(client)
    fake_course = IrregularCourse(id='34888', name='PBL 학생 OT', year='2026')
    fake_lectures = [Lecture(id='5001', title='<b>OT</b>')]
    fake_job = LectureDownloadJob(
        id=1, course_id='34888', course_name='PBL 학생 OT', lecture_id='5001', lecture_title='<b>OT</b>',
    )

    with (
        patch(
            'apps.site.views.EcampusCourseService.find_irregular_course',
            return_value=fake_course,
        ),
        patch('apps.site.views.EcampusCourseService.list_lectures', return_value=fake_lectures),
        patch('apps.site.views.LectureDownloadOrchestrator.start', return_value=fake_job),
    ):
        response = client.post(reverse('site:lab-lecture-irregular-download'), {
            'course_id': '34888', 'lecture_id': '5001', 'year': '2026',
        })

    body = response.content.decode()
    assert response.status_code == 200
    assert '&lt;b&gt;OT&lt;/b&gt;' in body
    assert '<b>OT</b>' not in body
