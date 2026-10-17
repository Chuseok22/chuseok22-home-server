from datetime import date
from unittest.mock import patch

import pytest
from django import forms

from apps.sejong.lecture.models import SejongAccount
from apps.site.forms import (
    IrregularCourseSelectForm,
    IrregularDownloadRequestForm,
    LectureCourseSelectForm,
    LectureDownloadRequestForm,
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
    assert form.cleaned_data == {'course_id': '', 'year': '2026', 'account_id': None}


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


_ACCOUNT_FORM_BASE_DATA = [
    (LectureCourseSelectForm, {'year': '2026', 'semester': '20'}),
    (LectureDownloadRequestForm, {'course_id': '1', 'lecture_id': '2', 'year': '2026', 'semester': '20'}),
    (IrregularCourseSelectForm, {'year': '2026'}),
    (IrregularDownloadRequestForm, {'course_id': '1', 'lecture_id': '2', 'year': '2026'}),
]


@pytest.mark.parametrize('form_class, base_data', _ACCOUNT_FORM_BASE_DATA)
@pytest.mark.parametrize('extra', [{}, {'account_id': ''}])
def test_계정_id가_없거나_비어있으면_DB_조회_없이_None이다(
    form_class: type[forms.Form], base_data: dict[str, str], extra: dict[str, str],
) -> None:
    form = form_class(data={**base_data, **extra})

    assert form.is_valid()
    assert form.cleaned_data['account_id'] is None


@pytest.mark.django_db
@pytest.mark.parametrize('form_class, base_data', _ACCOUNT_FORM_BASE_DATA)
def test_존재하는_계정_id는_정수로_통과한다(form_class: type[forms.Form], base_data: dict[str, str]) -> None:
    account = SejongAccount.objects.create(label='친구', student_id='1', password='pw')

    form = form_class(data={**base_data, 'account_id': str(account.id)})

    assert form.is_valid()
    assert form.cleaned_data['account_id'] == account.id


@pytest.mark.django_db
@pytest.mark.parametrize('form_class, base_data', _ACCOUNT_FORM_BASE_DATA)
def test_존재하지_않는_계정_id는_거부한다(form_class: type[forms.Form], base_data: dict[str, str]) -> None:
    account = SejongAccount.objects.create(label='삭제될계정', student_id='1', password='pw')
    deleted_id = account.id
    account.delete()

    form = form_class(data={**base_data, 'account_id': str(deleted_id)})

    assert not form.is_valid()
    assert 'account_id' in form.errors


@pytest.mark.django_db
@pytest.mark.parametrize('form_class, base_data', _ACCOUNT_FORM_BASE_DATA)
@pytest.mark.parametrize('invalid_value', ['abc', '0', '-1', str(2**63)])
def test_잘못된_형식의_계정_id는_거부한다(
    form_class: type[forms.Form], base_data: dict[str, str], invalid_value: str,
) -> None:
    form = form_class(data={**base_data, 'account_id': invalid_value})

    assert not form.is_valid()
    assert 'account_id' in form.errors
