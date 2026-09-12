from unittest.mock import MagicMock, patch

import requests

from apps.sejong.lecture.services.course import Course, EcampusCourseService, Lecture
from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService, EcampusSession

_NON_LOGIN_URL = 'https://ecampus.sejong.ac.kr/my/'
_LOGIN_URL = 'https://ecampus.sejong.ac.kr/login/index.php'
_LOGIN_URL_ALT = 'https://ecampus.sejong.ac.kr/login.php'

_CURRENT_COURSES_HTML = '''
<html><body>
<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=x">로그아웃</a>
<ul class="my-course-lists">
  <li><div class="course-box">
    <a href="https://ecampus.sejong.ac.kr/course/view.php?id=33293" class="course-link">
      <div class="course-name">
        <div class="course-label"><div class="badge badge-course">교과</div></div>
        <div class="course-title"><h3>알고리즘및실습 (011495-003)
          <span class="semester-name">(2학기)</span></h3><span class="prof">우현수</span></div>
      </div>
    </a>
  </div></li>
  <li><div class="course-box">
    <a href="https://ecampus.sejong.ac.kr/course/view.php?id=33229" class="course-link">
      <div class="course-name">
        <div class="course-label"><div class="badge badge-course">교과</div></div>
        <div class="course-title"><h3>컴퓨터게임과메타버스 (011317-001)
          <span class="semester-name">(2학기)</span></h3><span class="prof">한창완</span></div>
      </div>
    </a>
  </div></li>
</ul>
</body></html>
'''

_LECTURES_HTML = '''
<html><body>
<ul>
  <li class="activity vod modtype_vod" id="module-376940">
    <a href="mod/vod/view.php?id=376940">
      <span class="instancename">1주차_1차시_OT, 우선순위큐(1)<span class="accesshide"> 동영상</span></span>
    </a>
  </li>
  <li class="activity label modtype_label" id="module-999999">
    <span>공지사항</span>
  </li>
</ul>
</body></html>
'''

_VIEWER_HTML = '''
<html><body><script>
var streamUrl = "https://32bpbuqp8241.edge.naverncp.com/hls/abc/f0872056/mp4/f0872056.mp4/index.m3u8";
</script></body></html>
'''


def _fake_response(text: str, url: str = _NON_LOGIN_URL) -> MagicMock:
    response = MagicMock()
    response.url = url
    response.text = text
    response.raise_for_status = MagicMock()
    return response


def _session_returning(*responses: MagicMock) -> EcampusSession:
    """호출할 때마다 순서대로 다른 응답을 반환하는 가짜 EcampusSession."""
    http_session = MagicMock()
    http_session.get.side_effect = list(responses)
    return EcampusSession(session=http_session)


def _patch_create_session(*sessions: EcampusSession | None):
    """EcampusMoodleAuthService.create_session이 호출될 때마다 순서대로 값을 반환하도록 패치한다.

    fetch_with_retry는 만료 감지 시 create_session(force_refresh=True, ...)을 다시 호출하므로,
    최초 세션과 재인증 세션을 각각 지정할 수 있어야 한다.
    """
    return patch.object(EcampusMoodleAuthService, 'create_session', side_effect=list(sessions))


def test_list_courses_parses_dashboard_widget_and_dedupes_by_course_id() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(_CURRENT_COURSES_HTML))

    with _patch_create_session(session):
        courses = service.list_courses()

    assert courses == [
        Course(id='33293', name='알고리즘및실습 (011495-003)'),
        Course(id='33229', name='컴퓨터게임과메타버스 (011317-001)'),
    ]


def test_list_courses_returns_empty_list_on_request_exception() -> None:
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.side_effect = requests.RequestException('network error')
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        assert service.list_courses() == []


def test_list_courses_retries_once_when_not_authenticated_and_succeeds() -> None:
    """logout.php가 없는 응답(비인증 상태)이 오면 강제 재인증 후 재시도해 성공한다."""
    service = EcampusCourseService()
    not_authenticated = _session_returning(_fake_response('<html><body>로그인 필요</body></html>'))
    authenticated = _session_returning(_fake_response(_CURRENT_COURSES_HTML))

    with _patch_create_session(not_authenticated, authenticated):
        courses = service.list_courses()

    assert courses == [
        Course(id='33293', name='알고리즘및실습 (011495-003)'),
        Course(id='33229', name='컴퓨터게임과메타버스 (011317-001)'),
    ]


def test_list_courses_returns_empty_list_when_still_not_authenticated_after_retry() -> None:
    service = EcampusCourseService()
    not_authenticated = _session_returning(_fake_response('<html><body>로그인 필요</body></html>'))
    still_not_authenticated = _session_returning(
        _fake_response('<html><body>로그인 필요</body></html>'),
    )

    with _patch_create_session(not_authenticated, still_not_authenticated):
        assert service.list_courses() == []


def test_list_courses_logs_warning_when_authenticated_but_empty(caplog) -> None:
    """인증은 정상(logout.php 존재)인데 강좌가 0개로 파싱되면 재발 방지용 warning을 남긴다."""
    service = EcampusCourseService()
    session = _session_returning(
        _fake_response('<html><body><a href="logout.php">로그아웃</a></body></html>'),
    )

    with _patch_create_session(session):
        with caplog.at_level('WARNING'):
            courses = service.list_courses()

    assert courses == []
    assert any('0개로 파싱' in record.message for record in caplog.records)


def test_list_courses_does_not_log_warning_when_not_authenticated(caplog) -> None:
    """인증 자체가 안 된 경우(재시도까지 실패)는 별도 경로에서 이미 로그를 남기므로 이 경고는
    남기지 않는다."""
    service = EcampusCourseService()
    not_authenticated = _session_returning(_fake_response('<html><body>로그인 필요</body></html>'))
    still_not_authenticated = _session_returning(
        _fake_response('<html><body>로그인 필요</body></html>'),
    )

    with _patch_create_session(not_authenticated, still_not_authenticated):
        with caplog.at_level('WARNING'):
            service.list_courses()

    assert not any('0개로 파싱' in record.message for record in caplog.records)


def test_list_lectures_ignores_non_vod_activities_and_strips_accesshide_text() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(_LECTURES_HTML))

    with _patch_create_session(session):
        lectures = service.list_lectures(course_id='33293')

    assert lectures == [Lecture(id='376940', title='1주차_1차시_OT, 우선순위큐(1)')]


def test_list_lectures_returns_empty_list_when_no_vod_activities() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response('<html><body><ul></ul></body></html>'))

    with _patch_create_session(session):
        assert service.list_lectures(course_id='33293') == []


def test_get_stream_url_extracts_m3u8_url_from_html() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(_VIEWER_HTML))

    with _patch_create_session(session):
        stream_url = service.get_stream_url(lecture_id='376940')

    assert stream_url == (
        'https://32bpbuqp8241.edge.naverncp.com/hls/abc/f0872056/mp4/f0872056.mp4/index.m3u8'
    )


def test_get_stream_url_returns_none_when_not_found_in_body() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response('<html><body>no stream here</body></html>'))

    with _patch_create_session(session):
        assert service.get_stream_url(lecture_id='000000') is None


def test_get_stream_url_returns_none_on_request_exception() -> None:
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.side_effect = requests.RequestException('network error')
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        assert service.get_stream_url(lecture_id='376940') is None


def test_get_stream_url_does_not_cache_across_calls() -> None:
    """TTL이 짧을 수 있으므로 매 호출마다 새로 조회해야 한다(캐시 금지)."""
    service = EcampusCourseService()
    first_url = 'https://cdn.example.com/token-1/index.m3u8'
    second_url = 'https://cdn.example.com/token-2/index.m3u8'
    session1 = _session_returning(_fake_response(f'<script>"{first_url}"</script>'))
    session2 = _session_returning(_fake_response(f'<script>"{second_url}"</script>'))

    with _patch_create_session(session1):
        result1 = service.get_stream_url(lecture_id='1')
    with _patch_create_session(session2):
        result2 = service.get_stream_url(lecture_id='1')

    assert result1 == first_url
    assert result2 == second_url


def test_is_moodle_login_redirect_recognizes_both_login_paths() -> None:
    from apps.sejong.lecture.services.course import _is_moodle_login_redirect

    assert _is_moodle_login_redirect(_fake_response('', url=_LOGIN_URL)) is True
    assert _is_moodle_login_redirect(_fake_response('', url=_LOGIN_URL_ALT)) is True
    assert _is_moodle_login_redirect(_fake_response('', url=_NON_LOGIN_URL)) is False


def test_is_authenticated_page_checks_logout_link_presence() -> None:
    from apps.sejong.lecture.services.course import _is_authenticated_page

    assert _is_authenticated_page(_fake_response('<a href="logout.php">로그아웃</a>')) is True
    assert _is_authenticated_page(_fake_response('<p>로그인이 필요합니다</p>')) is False
