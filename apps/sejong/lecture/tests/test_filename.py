from apps.sejong.lecture.services.filename import build_lecture_filename


def test_sanitize_replaces_forbidden_characters_and_whitespace() -> None:
    result = build_lecture_filename('AI/ML: 개론', '1강', job_id=1)

    assert result == 'AI_ML_개론_1강_1.mp4'


def test_sanitize_collapses_consecutive_forbidden_runs_into_single_underscore() -> None:
    result = build_lecture_filename('자료구조   실습', '1강', job_id=1)

    assert result == '자료구조_실습_1강_1.mp4'


def test_sanitize_leaves_safe_characters_untouched() -> None:
    result = build_lecture_filename('컴퓨터게임과메타버스', '02주차1강', job_id=1)

    assert result == '컴퓨터게임과메타버스_02주차1강_1.mp4'


def test_build_lecture_filename_with_job_id_appends_id_suffix() -> None:
    result = build_lecture_filename('자료구조', '1주차 강의', job_id=42)

    assert result == '자료구조_1주차_강의_42.mp4'


def test_build_lecture_filename_without_job_id_omits_suffix() -> None:
    result = build_lecture_filename('자료구조', '1주차 강의', job_id=None)

    assert result == '자료구조_1주차_강의.mp4'


def test_build_lecture_filename_defaults_job_id_to_none() -> None:
    result = build_lecture_filename('자료구조', '1주차 강의')

    assert result == '자료구조_1주차_강의.mp4'


def test_build_lecture_filename_does_not_truncate_when_within_budget() -> None:
    course_name = '가' * 60
    lecture_title = '주차'

    result = build_lecture_filename(course_name, lecture_title, job_id=1)

    assert result == f"{'가' * 60}_주차_1.mp4"


def test_build_lecture_filename_truncates_by_byte_budget_prioritizing_lecture_title() -> None:
    """이름 부분(course+lecture) 총 200바이트 예산, course_name 최소 20바이트 보장.
    lecture_title이 예산을 다 채우면(180바이트=한글 60자) course_name은 남은
    20바이트(한글 6자)로 잘린다."""
    course_name = '가' * 100
    lecture_title = '나' * 100

    result = build_lecture_filename(course_name, lecture_title, job_id=7)

    assert result == f"{'가' * 6}_{'나' * 60}_7.mp4"
