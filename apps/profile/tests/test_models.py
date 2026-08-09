import pytest

from apps.profile.models import (
    Activity,
    ActivityAttachment,
    Career,
    Certification,
    Profile,
    PullRequestHighlight,
    Skill,
    VisitorCounter,
)


@pytest.mark.django_db
def test_profile_str_representation은_이름을_반환한다() -> None:
    profile = Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    assert str(profile) == '백지훈'


@pytest.mark.django_db
def test_visitor_counter_str_representation은_누적_방문수를_보여준다() -> None:
    counter = VisitorCounter.objects.create(pk=1, count=10)

    assert str(counter) == '누적 방문 10회'


@pytest.mark.django_db
def test_skill_str_representation은_분류와_이름을_보여준다() -> None:
    skill = Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    assert str(skill) == '[Backend] Django'


@pytest.mark.django_db
def test_skill은_category_다음_order_순으로_정렬된다() -> None:
    Skill.objects.create(category=Skill.Category.FRONTEND, name='React', order=0)
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=1)
    Skill.objects.create(category=Skill.Category.BACKEND, name='DRF', order=0)

    names = list(Skill.objects.values_list('name', flat=True))

    assert names == ['DRF', 'Django', 'React']


@pytest.mark.django_db
def test_career_str_representation은_분류_기관_역할을_보여준다() -> None:
    career = Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2022-03-01', order=0,
    )

    assert str(career) == '[학력] 세종대학교 — 컴퓨터공학과'


@pytest.mark.django_db
def test_career는_order_순으로_정렬된다() -> None:
    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=101,
    )
    Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2022-03-01', order=100,
    )

    first = Career.objects.filter(organization__in=['추석22', '세종대학교']).order_by('order').first()

    assert first.organization == '세종대학교'


@pytest.mark.django_db
def test_activity_str_representation은_이름을_반환한다() -> None:
    activity = Activity.objects.create(name='동아리 스터디 운영', start_year=2024, order=0)

    assert str(activity) == '동아리 스터디 운영'


@pytest.mark.django_db
def test_activity_years는_start_year만_있으면_단일_연도_리스트를_반환한다() -> None:
    activity = Activity.objects.create(name='단일연도 활동', start_year=2026, order=0)

    assert activity.years == [2026]


@pytest.mark.django_db
def test_activity_years는_start_year와_end_year_사이_모든_연도를_반환한다() -> None:
    activity = Activity.objects.create(name='다년도 활동', start_year=2022, end_year=2023, order=0)

    assert activity.years == [2022, 2023]


@pytest.mark.django_db
def test_activity_clean은_end_year가_start_year보다_빠르면_검증오류를_발생시킨다() -> None:
    from django.core.exceptions import ValidationError

    activity = Activity(name='역전된 연도 활동', start_year=2024, end_year=2020, order=0)

    with pytest.raises(ValidationError) as exc_info:
        activity.clean()

    assert 'end_year' in exc_info.value.message_dict


@pytest.mark.django_db
def test_activity는_end_year가_start_year보다_빠르면_db_제약으로_저장을_거부한다() -> None:
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        Activity.objects.create(name='역전된 연도 활동(DB)', start_year=2024, end_year=2020, order=0)


@pytest.mark.django_db
def test_activity_links는_리스트가_아니면_검증오류를_발생시킨다() -> None:
    from django.core.exceptions import ValidationError

    activity = Activity(name='links 검증 테스트1', start_year=2026, links={'type': 'github', 'url': 'https://x'}, order=0)

    with pytest.raises(ValidationError):
        activity.full_clean()


@pytest.mark.django_db
def test_activity_links는_허용되지_않은_type이면_검증오류를_발생시킨다() -> None:
    from django.core.exceptions import ValidationError

    activity = Activity(
        name='links 검증 테스트2', start_year=2026,
        links=[{'type': '알수없는타입', 'url': 'https://example.com'}], order=0,
    )

    with pytest.raises(ValidationError):
        activity.full_clean()


@pytest.mark.django_db
def test_activity_links는_http_https가_아닌_url이면_검증오류를_발생시킨다() -> None:
    from django.core.exceptions import ValidationError

    activity = Activity(
        name='links 검증 테스트3', start_year=2026,
        links=[{'type': 'official', 'url': 'javascript:alert(1)'}], order=0,
    )

    with pytest.raises(ValidationError):
        activity.full_clean()


@pytest.mark.django_db
def test_activity_links는_유효한_링크는_검증을_통과한다() -> None:
    activity = Activity(
        name='links 검증 테스트4', start_year=2026,
        links=[{'type': 'github', 'url': 'https://github.com/example'}], order=0,
    )

    activity.full_clean()  # 예외가 발생하지 않아야 한다


@pytest.mark.django_db
def test_activityattachment_삭제시_저장소_파일도_함께_삭제된다(settings, tmp_path) -> None:
    from django.core.files.storage import default_storage
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='파일삭제 테스트 활동', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('cleanup.pdf', b'dummy-bytes'),
    )
    file_path = attachment.file.name
    assert default_storage.exists(file_path)

    attachment.delete()

    assert not default_storage.exists(file_path)


@pytest.mark.django_db
def test_activity_삭제시_연결된_attachment_파일도_함께_삭제된다(settings, tmp_path) -> None:
    from django.core.files.storage import default_storage
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='캐스케이드 파일삭제 테스트 활동', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('cascade.pdf', b'dummy-bytes'),
    )
    file_path = attachment.file.name
    assert default_storage.exists(file_path)

    activity.delete()

    assert not default_storage.exists(file_path)


@pytest.mark.django_db
def test_activity_attachment_str_representation은_label을_반환한다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='첨부파일 테스트 활동', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('cert.pdf', b'dummy-bytes'), label='수료증',
    )

    assert str(attachment) == '수료증'


@pytest.mark.django_db
def test_activity_attachment_str_representation은_label이_없으면_파일명만_반환한다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='첨부파일 테스트 활동2', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('notes.pdf', b'dummy-bytes'),
    )

    # file.name은 'activities/attachments/2026/08/notes.pdf'처럼 업로드 경로가 붙으므로,
    # display_name이 경로를 뺀 순수 파일명만 반환하는지 정확히 검증한다.
    assert attachment.display_name == 'notes.pdf'
    assert str(attachment) == 'notes.pdf'


@pytest.mark.django_db
def test_activity_attachment_emoji는_이미지_확장자면_사진_이모지를_반환한다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='이모지 테스트 활동1', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('photo.jpg', b'dummy-bytes'),
    )

    assert attachment.emoji == '🖼'


@pytest.mark.django_db
def test_activity_attachment_emoji는_문서_확장자면_문서_이모지를_반환한다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='이모지 테스트 활동2', start_year=2026, order=0)
    attachment = ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('report.pdf', b'dummy-bytes'),
    )

    assert attachment.emoji == '📄'


@pytest.mark.django_db
def test_activity가_삭제되면_attachment도_함께_삭제된다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='캐스케이드 테스트 활동', start_year=2026, order=0)
    ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('a.pdf', b'dummy-bytes'), label='자료',
    )

    activity.delete()

    assert ActivityAttachment.objects.count() == 0


@pytest.mark.django_db
def test_certification_str_representation은_이름과_발급기관을_보여준다() -> None:
    cert = Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
    )

    assert str(cert) == '정보처리기사 (한국산업인력공단)'


@pytest.mark.django_db
def test_certification은_credential_number와_credential_url_필드를_갖지_않는다() -> None:
    field_names = {field.name for field in Certification._meta.get_fields()}

    assert 'credential_number' not in field_names
    assert 'credential_url' not in field_names


@pytest.mark.django_db
def test_activity는_link_필드를_갖지_않는다() -> None:
    field_names = {field.name for field in Activity._meta.get_fields()}

    assert 'link' not in field_names
    assert 'links' in field_names


@pytest.mark.django_db
def test_pull_request_highlight_str_representation은_저장소와_제목을_보여준다() -> None:
    pr = PullRequestHighlight.objects.create(
        title='GitHub 활동 이력 자동 정리 기능 추가', repo_name='chuseok22/chuseok22-home-server',
        pr_url='https://github.com/Chuseok22/chuseok22-home-server/pull/62', order=0,
    )

    assert str(pr) == '[chuseok22/chuseok22-home-server] GitHub 활동 이력 자동 정리 기능 추가'


@pytest.mark.django_db
def test_시딩_마이그레이션으로_수상_2건이_생성되어_있다() -> None:
    awards = list(Career.objects.filter(category=Career.Category.AWARD).order_by('order'))

    assert len(awards) == 2
    assert awards[0].organization == '제4회 문화체육관광 인공지능·데이터 활용 공모전'
    assert awards[0].role == '문화데이터 우수사례 부문 장려상'
    assert awards[1].organization == '세종대학교'
    assert awards[1].role == '성적우수장학금'


@pytest.mark.django_db
def test_시딩_마이그레이션으로_활동_3건이_생성되어_있다() -> None:
    names = list(Activity.objects.order_by('order').values_list('name', flat=True))

    assert names == [
        'AROM Spring Boot 심화반 · Lead Mentor',
        'CODEGATE AI-Start-Up Hackathon',
        'Autory · 세종대 자동차제작 동아리',
    ]
