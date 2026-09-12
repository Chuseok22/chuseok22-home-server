from datetime import date

from django import forms

from apps.sejong.library.services.validation import validate_attendee_count


class LibraryDateForm(forms.Form):
    reserve_date = forms.RegexField(regex=r'^\d{8}$', label='조회 날짜 (YYYYMMDD)')
    room_type = forms.ChoiceField(
        choices=[('study_room', '스터디룸'), ('s_lounge', 'S-Lounge')],
        required=False,
        initial='study_room',
    )

    def clean_room_type(self) -> str:
        return self.cleaned_data.get('room_type') or 'study_room'


class LibraryReserveSlotForm(forms.Form):
    """가용 현황 그리드에서 선택한 슬롯 정보 (숨김 필드로 폼에 실려온다)."""

    room_no = forms.CharField(max_length=10)
    room_gb = forms.CharField(max_length=10)
    seat_cnt = forms.IntegerField(min_value=1)
    sroom_title = forms.CharField(max_length=100)
    room_name = forms.CharField(max_length=100)
    seq = forms.CharField(max_length=5)
    reserve_date = forms.RegexField(regex=r'^\d{8}$')
    start_time = forms.RegexField(regex=r'^\d{4}$')


class StudentSearchForm(forms.Form):
    name = forms.CharField(max_length=50, required=False)
    student_no = forms.CharField(max_length=20, required=False)

    def clean(self) -> dict:
        cleaned = super().clean()
        name = cleaned.get('name', '')
        student_no = cleaned.get('student_no', '')
        if bool(name) == bool(student_no):
            raise forms.ValidationError('이름 또는 학번 중 정확히 하나를 입력해야 합니다.')
        return cleaned


class LibraryReserveForm(LibraryReserveSlotForm):
    """예약 폼 제출 시 슬롯 정보 + 사용자가 입력하는 use_time·참여자."""

    use_time = forms.ChoiceField(choices=[(60, '60분'), (120, '120분')])
    attendees_raw = forms.CharField(
        label='참여자 (학번-이름, 쉼표로 구분)',
        help_text='예: 22011315-백지훈,22011316-홍길동',
    )

    def clean_attendees_raw(self) -> list[dict[str, str]]:
        raw = self.cleaned_data['attendees_raw']
        attendees = []
        for pair in raw.split(','):
            pair = pair.strip()
            if not pair:
                continue
            if '-' not in pair:
                raise forms.ValidationError(f'형식 오류: {pair} (학번-이름 형태여야 함)')
            student_id, name = pair.split('-', 1)
            attendees.append({'student_id': student_id.strip(), 'name': name.strip()})
        if not attendees:
            raise forms.ValidationError('참여자를 최소 1명 입력해야 합니다.')
        return attendees

    def clean(self) -> dict:
        cleaned = super().clean()
        seat_cnt = cleaned.get('seat_cnt')
        attendees = cleaned.get('attendees_raw')
        if seat_cnt is not None and attendees is not None:
            error = validate_attendee_count(seat_cnt, len(attendees))
            if error:
                raise forms.ValidationError(error)
        return cleaned


LECTURE_YEAR_CHOICES = [('all', '전체')] + [
    (str(year), str(year)) for year in range(date.today().year, 2002, -1)
]
LECTURE_SEMESTER_CHOICES = [
    ('all', '전체'),
    ('10', '1학기'),
    ('11', '여름계절수업'),
    ('20', '2학기'),
    ('21', '겨울계절수업'),
]


class LectureCourseSelectForm(forms.Form):
    """강좌 조회(course_id 없음) 또는 강의 목록 조회(course_id 있음) 요청.

    year/semester는 항상 필수다 - "이번 학기 전용 자동 조회" 경로가 없어져 모든 조회가
    EcampusCourseService.search_past_courses()를 거치므로, 조회 대상 학기를 반드시 명시해야 한다.
    """

    course_id = forms.CharField(max_length=20, required=False)
    year = forms.ChoiceField(choices=LECTURE_YEAR_CHOICES)
    semester = forms.ChoiceField(choices=LECTURE_SEMESTER_CHOICES)


class LectureDownloadRequestForm(forms.Form):
    """강의 다운로드 요청 검증. course_name/lecture_title은 뷰가 서버에서 다시 조회해 확정하므로
    (클라이언트 제출값을 신뢰하지 않음) 여기서 받지 않는다. year/semester도 필수다 -
    find_course()가 어느 학기에서 강좌를 재검증할지 서버가 항상 알아야 한다."""

    course_id = forms.CharField(max_length=20)
    lecture_id = forms.CharField(max_length=20)
    year = forms.ChoiceField(choices=LECTURE_YEAR_CHOICES)
    semester = forms.ChoiceField(choices=LECTURE_SEMESTER_CHOICES)


def default_lecture_year_and_semester() -> tuple[str, str]:
    """오늘 날짜 기준으로 현재 학기의 (연도, 학기 코드)를 근사치로 추정한다. 계절학기 경계 등
    실제 학사 일정과 정확히 일치하지 않을 수 있으나, 사용자가 드롭다운을 직접 바꿀 수 있으므로
    근사치로 충분하다. 겨울계절수업(1~2월)은 전년도 학사년도에 속하므로 연도를 하나 뺀다 -
    2027년 1월이면 ('2026', '21')을 반환한다."""
    today = date.today()
    month = today.month
    if month in (1, 2):
        return str(today.year - 1), '21'
    if 3 <= month <= 6:
        return str(today.year), '10'
    if month in (7, 8):
        return str(today.year), '11'
    return str(today.year), '20'


class PlaceSuggestionForm(forms.Form):
    restaurant_name = forms.CharField(max_length=100, label='상호명')
    kakao_place_url = forms.URLField(required=False, label='카카오맵 링크')
    message = forms.CharField(required=False, widget=forms.Textarea, label='추천 이유')


class PostEditForm(forms.Form):
    """블로그 글 인라인 수정 폼. BlogIngestSerializer(apps/blog/serializers.py)와 동일한 길이 제약을 맞춘다."""

    title = forms.CharField(max_length=200)
    summary = forms.CharField(max_length=300, required=False)
    content = forms.CharField(max_length=50000)
