from datetime import date
from unittest.mock import patch

from apps.site.forms import (
    IrregularCourseSelectForm,
    IrregularDownloadRequestForm,
    default_lecture_year_and_semester,
    lecture_year_choices,
)


def test_1월에는_전년도_겨울계절수업으로_계산된다() -> None:
    with patch('apps.site.forms.date') as mock_date:
        mock_date.today.return_value = date(2027, 1, 15)
        assert default_lecture_year_and_semester() == ('2026', '21')


def test_3월에는_당해년도_1학기로_계산된다() -> None:
    with patch('apps.site.forms.date') as mock_date:
        mock_date.today.return_value = date(2027, 3, 15)
        assert default_lecture_year_and_semester() == ('2027', '10')


def test_9월에는_당해년도_2학기로_계산된다() -> None:
    with patch('apps.site.forms.date') as mock_date:
        mock_date.today.return_value = date(2027, 9, 15)
        assert default_lecture_year_and_semester() == ('2027', '20')


def test_연도_선택지는_호출할_때마다_현재_연도를_반영한다() -> None:
    """LECTURE_YEAR_CHOICES가 모듈 로드 시점에 한 번만 계산되던 예전 버그의 회귀 테스트 -
    lecture_year_choices()는 매 호출마다 date.today()를 다시 읽어야 한다."""
    with patch('apps.site.forms.date') as mock_date:
        mock_date.today.return_value = date(2030, 6, 1)
        choices = lecture_year_choices()

    assert ('2030', '2030') in choices
    assert ('all', '전체') == choices[0]


def test_비교과_강좌_조회_폼은_연도만_필수다() -> None:
    form = IrregularCourseSelectForm(data={'year': '2026'})

    assert form.is_valid()
    assert form.cleaned_data == {'course_id': '', 'year': '2026'}


def test_비교과_강좌_조회_폼은_전체_연도를_허용한다() -> None:
    assert IrregularCourseSelectForm(data={'year': 'all'}).is_valid()


def test_비교과_강좌_조회_폼은_연도가_없으면_거부한다() -> None:
    assert not IrregularCourseSelectForm(data={}).is_valid()


def test_비교과_강좌_조회_폼은_잘못된_연도를_거부한다() -> None:
    assert not IrregularCourseSelectForm(data={'year': '1999'}).is_valid()


def test_비교과_다운로드_폼은_course_id_lecture_id_year가_모두_필요하다() -> None:
    valid = IrregularDownloadRequestForm(
        data={'course_id': '34888', 'lecture_id': '5001', 'year': '2026'},
    )
    missing_lecture = IrregularDownloadRequestForm(
        data={'course_id': '34888', 'year': '2026'},
    )

    assert valid.is_valid()
    assert not missing_lecture.is_valid()
