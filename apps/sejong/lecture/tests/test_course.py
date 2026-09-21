from unittest.mock import MagicMock, patch

import requests

from apps.sejong.lecture.services.course import (
    Course,
    EcampusCourseService,
    IrregularCourse,
    Lecture,
)
from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService, EcampusSession

_NON_LOGIN_URL = 'https://ecampus.sejong.ac.kr/my/'
_LOGIN_URL = 'https://ecampus.sejong.ac.kr/login/index.php'
_LOGIN_URL_ALT = 'https://ecampus.sejong.ac.kr/login.php'

_PAST_COURSES_HTML = '''
<html><body>
<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=x">로그아웃</a>
<table><tbody class="my-course-lists">
<tr><td>2023</td><td>2학기</td><td>
  <div class="course-flex"><span class="badge badge-course">교과</span>
  <a href="https://ecampus.sejong.ac.kr/course/view.php?id=31245" class="coursefullname">
    공업수학1 (000304-003)</a></div>
</td></tr>
<tr><td>2023</td><td>1학기</td><td>
  <div class="course-flex"><span class="badge badge-course">교과</span>
  <a href="https://ecampus.sejong.ac.kr/course/view.php?id=31493" class="coursefullname">
    컴퓨터네트워크 (003284-003)</a></div>
</td></tr>
</tbody></table>
</body></html>
'''

_UNKNOWN_SEMESTER_LABEL_HTML = '''
<html><body>
<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=x">로그아웃</a>
<table><tbody>
<tr><td>2023</td><td>동계특별학기</td><td>
  <a href="https://ecampus.sejong.ac.kr/course/view.php?id=99001" class="coursefullname">
    특별강좌</a>
</td></tr>
</tbody></table>
</body></html>
'''

_UNKNOWN_YEAR_LABEL_HTML = '''
<html><body>
<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=x">로그아웃</a>
<table><tbody>
<tr><td>알수없음</td><td>1학기</td><td>
  <a href="https://ecampus.sejong.ac.kr/course/view.php?id=99002" class="coursefullname">
    연도미상강좌</a>
</td></tr>
</tbody></table>
</body></html>
'''

_MISSING_YEAR_SEMESTER_CELLS_HTML = '''
<html><body>
<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=x">로그아웃</a>
<table><tbody>
<tr><td>
  <a href="https://ecampus.sejong.ac.kr/course/view.php?id=99003" class="coursefullname">
    셀누락강좌</a>
</td></tr>
</tbody></table>
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

# 실제 viewer.php 응답 구조를 마스킹한 픽스처 - 스트림 URL이 <video data-setup-lazy> JSON 안에
# 슬래시가 `\/`로 이스케이프된 채 들어 있다. `\/`를 그대로 두려면 raw 문자열이어야 한다.
_VIEWER_HTML = r'''
<html><body>
<div id="vod_viewer">
<video id="my-video" class="video-js vjs-default-skin" poster="https://cdn.example.com/thumbnail/tn_1.png" data-setup-lazy='{"language":"ko","fluid":true,"sources":{"src":"https:\/\/cdn.example.com\/hls\/TOKEN\/lecture-id\/mp4\/lecture-id.mp4\/index.m3u8","type":"application\/x-mpegURL"}}'>
<p class="vjs-no-js">JavaScript가 필요합니다.</p>
</video>
</div>
</body></html>
'''

_PLAIN_M3U8_URL = 'https://cdn.example.com/hls/TOKEN/plain/index.m3u8'


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
        'https://cdn.example.com/hls/TOKEN/lecture-id/mp4/lecture-id.mp4/index.m3u8'
    )


def _get_stream_url_from(html: str) -> str | None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(html))

    with _patch_create_session(session):
        return service.get_stream_url(lecture_id='376940')


def test_get_stream_url_returns_none_when_player_config_json_is_broken_and_no_plain_url() -> None:
    html = "<html><body><video data-setup-lazy='{not json'></video></body></html>"

    assert _get_stream_url_from(html) is None


def test_get_stream_url_falls_back_to_plain_url_when_player_config_json_is_broken() -> None:
    html = (
        "<html><body><video data-setup-lazy='{not json'></video>"
        f'<script>var streamUrl = "{_PLAIN_M3U8_URL}";</script></body></html>'
    )

    assert _get_stream_url_from(html) == _PLAIN_M3U8_URL


def test_get_stream_url_returns_none_when_player_config_src_is_not_https() -> None:
    html = (
        "<html><body><video data-setup-lazy='"
        '{"sources":{"src":"http:\\/\\/cdn.example.com\\/hls\\/TOKEN\\/index.m3u8"}}'
        "'></video></body></html>"
    )

    assert _get_stream_url_from(html) is None


def test_get_stream_url_returns_none_when_player_config_has_no_sources() -> None:
    html = "<html><body><video data-setup-lazy='{\"language\":\"ko\"}'></video></body></html>"

    assert _get_stream_url_from(html) is None


def test_get_stream_url_falls_back_to_plain_url_when_player_config_is_absent() -> None:
    html = f'<html><body><script>var streamUrl = "{_PLAIN_M3U8_URL}";</script></body></html>'

    assert _get_stream_url_from(html) == _PLAIN_M3U8_URL


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


def test_search_past_courses_parses_table_including_year_and_semester_code() -> None:
    """같은 <tr> 안의 연도/학기 <td>를 강좌명과 함께 파싱하고, 학기는 라벨이 아니라
    코드값('10'/'11'/'20'/'21')으로 저장한다 - 폼 select 값·재조회 쿼리 파라미터와 맞추기 위함."""
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.return_value = _fake_response(_PAST_COURSES_HTML)
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        courses = service.search_past_courses(year='2023', semester='all')

    assert courses == [
        Course(id='31245', name='공업수학1 (000304-003)', year='2023', semester='20'),
        Course(id='31493', name='컴퓨터네트워크 (003284-003)', year='2023', semester='10'),
    ]
    http_session.get.assert_called_once()
    _, kwargs = http_session.get.call_args
    assert kwargs['params'] == {'year': '2023', 'semester': 'all'}


def test_search_past_courses_maps_unknown_semester_label_to_all() -> None:
    """알 수 없는 학기 라벨은 'all' 코드로 폴백한다 - ChoiceField가 거부하지 않는 값이어야
    이 강좌를 클릭했을 때 강의 목록 조회/다운로드가 계속 동작한다(그룹 헤더 표시만 다소
    어색해질 뿐 - 수용 가능한 트레이드오프)."""
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.return_value = _fake_response(_UNKNOWN_SEMESTER_LABEL_HTML)
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        courses = service.search_past_courses(year='2023', semester='all')

    assert courses == [Course(id='99001', name='특별강좌', year='2023', semester='all')]


def test_search_past_courses_maps_unknown_year_label_to_all() -> None:
    """연도 셀이 숫자가 아니면 'all' 코드로 폴백한다 - semester와 동일한 이유로, ChoiceField가
    거부하지 않는 값이어야 이 강좌를 클릭했을 때 조회가 실패하지 않는다."""
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.return_value = _fake_response(_UNKNOWN_YEAR_LABEL_HTML)
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        courses = service.search_past_courses(year='2023', semester='all')

    assert courses == [Course(id='99002', name='연도미상강좌', year='all', semester='10')]


def test_search_past_courses_skips_row_with_missing_cells_and_logs_warning(caplog) -> None:
    """연도/학기 <td>가 부족한 행은 강좌를 건너뛰되, HTML 구조 변경을 감지할 수 있도록
    warning을 남긴다."""
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.return_value = _fake_response(_MISSING_YEAR_SEMESTER_CELLS_HTML)
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        with caplog.at_level('WARNING'):
            courses = service.search_past_courses(year='2023', semester='all')

    assert courses == []
    assert any('99003' in record.getMessage() for record in caplog.records)


def test_search_past_courses_returns_empty_list_when_not_authenticated() -> None:
    service = EcampusCourseService()
    not_authenticated = _session_returning(_fake_response('<html><body>로그인 필요</body></html>'))
    still_not_authenticated = _session_returning(
        _fake_response('<html><body>로그인 필요</body></html>'),
    )

    with _patch_create_session(not_authenticated, still_not_authenticated):
        assert service.search_past_courses(year='2023', semester='10') == []


def test_search_past_courses_returns_empty_list_on_request_exception() -> None:
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.side_effect = requests.RequestException('network error')
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        assert service.search_past_courses(year='2023', semester='10') == []


def test_search_past_courses_empty_result_does_not_log_warning(caplog) -> None:
    """과거강좌가 0개인 것은 정상 상황(이력 없음)이므로 warning을 남기지 않는다."""
    service = EcampusCourseService()
    session = _session_returning(
        _fake_response('<html><body><a href="logout.php">로그아웃</a></body></html>'),
    )

    with _patch_create_session(session):
        with caplog.at_level('WARNING'):
            courses = service.search_past_courses(year='2003', semester='10')

    assert courses == []
    assert len(caplog.records) == 0


def test_find_course_uses_search_past_courses_and_returns_matching_course() -> None:
    service = EcampusCourseService()
    target = Course(id='201', name='이산수학', year='2023', semester='10')

    with patch.object(EcampusCourseService, 'search_past_courses', return_value=[target]) as mock_past:
        result = service.find_course('201', year='2023', semester='10')

    assert result == target
    mock_past.assert_called_once_with(year='2023', semester='10')


def test_find_course_returns_none_when_not_found() -> None:
    service = EcampusCourseService()

    with patch.object(EcampusCourseService, 'search_past_courses', return_value=[]):
        assert service.find_course('999', year='2023', semester='10') is None


_MY_PAGE_URL = 'https://ecampus.sejong.ac.kr/local/ubassistant/my.php'


def _irregular_pagination_link(number: int, active_page: int) -> str:
    """현재 페이지 링크의 href는 '#', 다른 페이지는 실제 URL이다(실측)."""
    href = '#' if number == active_page else f'{_MY_PAGE_URL}?year=all&amp;page={number}'
    active_class = ' active' if number == active_page else ''
    return (
        f'<li class="page-item{active_class}">'
        f'<a class="nav_paging page-link" href="{href}">{number}</a></li>'
    )


def _irregular_page_html(
    rows: list[tuple[str, str, str]],
    page_numbers: tuple[int, ...] = (1,),
    active_page: int = 1,
    authenticated: bool = True,
) -> str:
    """`local/ubassistant/my.php` 응답을 흉내낸 HTML(실측 구조). rows는 (연도, 강좌 id, 강좌명) 목록."""
    logout_link = (
        '<a href="https://ecampus.sejong.ac.kr/login/logout.php?sesskey=MASKED">로그아웃</a>'
        if authenticated
        else ''
    )
    table_rows = ''.join(
        f'<tr><td class="text-center">{year}</td>'
        f'<td><a href="https://ecampus.sejong.ac.kr/course/view.php?id={course_id}">{name}</a></td>'
        '<td class="text-center"></td></tr>'
        for year, course_id, name in rows
    )
    pagination = ''.join(
        _irregular_pagination_link(number, active_page) for number in page_numbers
    )
    return (
        f'<html><body>{logout_link}'
        '<table class="table table-striped table-bordered table-coursemos">'
        '<thead><tr><th class="header">년도</th><th class="header">강좌명</th>'
        '<th class="header">교수</th></tr></thead>'
        f'<tbody>{table_rows}</tbody></table>'
        f'<div class="text-center mt-3"><ul class="pagination justify-content-center">'
        f'{pagination}</ul></div>'
        '</body></html>'
    )


def _requested_params(session: EcampusSession) -> list[dict[str, object]]:
    return [call.kwargs['params'] for call in session.session.get.call_args_list]


def test_search_irregular_courses_parses_year_id_and_name_ignoring_professor_column() -> None:
    service = EcampusCourseService()
    html = _irregular_page_html([
        ('2026', '34888', '2026-2학기 PBL 학생 OT (PBLT-02)'),
        ('2024', '11800', '2024학년도 FL 학생 OT (FLLT-01)'),
    ])
    session = _session_returning(_fake_response(html))

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert courses == [
        IrregularCourse(id='34888', name='2026-2학기 PBL 학생 OT (PBLT-02)', year='2026'),
        IrregularCourse(id='11800', name='2024학년도 FL 학생 OT (FLLT-01)', year='2024'),
    ]


def test_search_irregular_courses_requests_my_php_with_year_and_first_page() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(_irregular_page_html([])))

    with _patch_create_session(session):
        service.search_irregular_courses(year='2026')

    assert _requested_params(session) == [{'year': '2026', 'page': 1}]


def test_search_irregular_courses_falls_back_to_all_when_year_cell_is_not_numeric() -> None:
    service = EcampusCourseService()
    html = _irregular_page_html([('', '34888', '강좌 A'), ('상시', '34889', '강좌 B')])
    session = _session_returning(_fake_response(html))

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert [course.year for course in courses] == ['all', 'all']


def test_search_irregular_courses_skips_rows_without_course_link() -> None:
    service = EcampusCourseService()
    html = _irregular_page_html([('2026', '34888', '강좌 A')]).replace(
        '</tbody>', '<tr><td colspan="3">등록된 강좌가 없습니다.</td></tr></tbody>',
    )
    session = _session_returning(_fake_response(html))

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert [course.id for course in courses] == ['34888']


def test_search_irregular_courses_returns_empty_list_when_no_rows() -> None:
    service = EcampusCourseService()
    session = _session_returning(_fake_response(_irregular_page_html([])))

    with _patch_create_session(session):
        assert service.search_irregular_courses(year='2025') == []


def test_search_irregular_courses_follows_pagination_and_merges_pages() -> None:
    service = EcampusCourseService()
    page_one = _irregular_page_html(
        [('2026', '34888', '강좌 A')], page_numbers=(1, 2), active_page=1,
    )
    page_two = _irregular_page_html(
        [('2023', '7695', '강좌 B')], page_numbers=(1, 2), active_page=2,
    )
    session = _session_returning(_fake_response(page_one), _fake_response(page_two))

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert [course.id for course in courses] == ['34888', '7695']
    assert _requested_params(session) == [
        {'year': 'all', 'page': 1}, {'year': 'all', 'page': 2},
    ]


def test_search_irregular_courses_deduplicates_courses_repeated_across_pages() -> None:
    service = EcampusCourseService()
    page_one = _irregular_page_html(
        [('2026', '34888', '강좌 A')], page_numbers=(1, 2), active_page=1,
    )
    page_two = _irregular_page_html(
        [('2026', '34888', '강좌 A')], page_numbers=(1, 2), active_page=2,
    )
    session = _session_returning(_fake_response(page_one), _fake_response(page_two))

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert [course.id for course in courses] == ['34888']


def test_search_irregular_courses_stops_at_max_pages() -> None:
    """페이지네이션에 99페이지가 보여도 상한(10페이지)까지만 요청한다."""
    service = EcampusCourseService()
    response = _fake_response(
        _irregular_page_html([('2026', '34888', '강좌 A')], page_numbers=(1, 99), active_page=1),
    )
    session = _session_returning(*[response] * 10)

    with _patch_create_session(session):
        courses = service.search_irregular_courses(year='all')

    assert [course.id for course in courses] == ['34888']
    assert session.session.get.call_count == 10


def test_search_irregular_courses_reauthenticates_once_when_session_expired() -> None:
    service = EcampusCourseService()
    expired = _session_returning(
        _fake_response(_irregular_page_html([], authenticated=False)),
    )
    fresh = _session_returning(
        _fake_response(_irregular_page_html([('2026', '34888', '강좌 A')])),
    )

    with _patch_create_session(expired, fresh):
        courses = service.search_irregular_courses(year='2026')

    assert [course.id for course in courses] == ['34888']


def test_search_irregular_courses_returns_empty_list_on_request_exception() -> None:
    service = EcampusCourseService()
    http_session = MagicMock()
    http_session.get.side_effect = requests.RequestException('network error')
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        assert service.search_irregular_courses(year='all') == []


def test_search_irregular_courses_returns_empty_list_when_second_page_request_fails() -> None:
    """중간 페이지가 실패하면 일부만 돌려주지 않고 전체를 실패(빈 목록)로 처리한다."""
    service = EcampusCourseService()
    page_one = _irregular_page_html(
        [('2026', '34888', '강좌 A')], page_numbers=(1, 2), active_page=1,
    )
    http_session = MagicMock()
    http_session.get.side_effect = [
        _fake_response(page_one), requests.RequestException('network error'),
    ]
    session = EcampusSession(session=http_session)

    with _patch_create_session(session):
        assert service.search_irregular_courses(year='all') == []


def test_find_irregular_course_returns_matching_course() -> None:
    service = EcampusCourseService()
    html = _irregular_page_html([('2026', '34888', '강좌 A'), ('2026', '31197', '강좌 B')])
    session = _session_returning(_fake_response(html))

    with _patch_create_session(session):
        course = service.find_irregular_course(course_id='31197', year='2026')

    assert course == IrregularCourse(id='31197', name='강좌 B', year='2026')


def test_find_irregular_course_returns_none_when_not_in_results() -> None:
    service = EcampusCourseService()
    session = _session_returning(
        _fake_response(_irregular_page_html([('2026', '34888', '강좌 A')])),
    )

    with _patch_create_session(session):
        assert service.find_irregular_course(course_id='99999', year='2026') is None


def test_parse_irregular_last_page_uses_largest_visible_page_number() -> None:
    from apps.sejong.lecture.services.course import _parse_irregular_last_page

    html = _irregular_page_html([], page_numbers=(1, 2, 3), active_page=1)

    assert _parse_irregular_last_page(html) == 3


def test_parse_irregular_last_page_returns_one_without_pagination() -> None:
    from apps.sejong.lecture.services.course import _parse_irregular_last_page

    assert _parse_irregular_last_page('<html><body>no pagination</body></html>') == 1
