from django import forms


class LibraryDateForm(forms.Form):
    reserve_date = forms.RegexField(regex=r'^\d{8}$', label='조회 날짜 (YYYYMMDD)')


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
