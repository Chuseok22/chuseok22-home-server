import datetime

from django.db import migrations


def seed_awards_and_activities(apps, schema_editor) -> None:
    Career = apps.get_model('profile', 'Career')
    Activity = apps.get_model('profile', 'Activity')

    Career.objects.create(
        category='award',
        organization='제4회 문화체육관광 인공지능·데이터 활용 공모전',
        role='문화데이터 우수사례 부문 장려상',
        description='MU:DAM 개발 총괄로 참여',
        period_start=datetime.date(2026, 8, 6),
        period_end=datetime.date(2026, 8, 6),
        order=0,
    )
    Career.objects.create(
        category='award',
        organization='세종대학교',
        role='성적우수장학금',
        description='2022-1학기 1위(GPA 4.5/4.5) · 2022-2학기 1위(GPA 4.5/4.5) · 2023-1학기 3위',
        period_start=datetime.date(2022, 3, 1),
        period_end=datetime.date(2023, 6, 30),
        order=1,
    )

    Activity.objects.create(
        name='AROM Spring Boot 심화반 · Lead Mentor',
        description=(
            '세종대학교 IT 개발 동아리 AROM에서 Spring Boot 기본 구조부터 심화 주제까지 다루는 '
            '커리큘럼을 직접 제작하고, 수강자 약 30명을 대상으로 리드멘토로 활동했습니다.'
        ),
        period='2024.2학기',
        order=0,
    )
    Activity.objects.create(
        name='CODEGATE AI-Start-Up Hackathon',
        description=(
            '3인 팀으로 참가해 24시간 안에 발달장애 아동을 위한 AI 행동지원 서비스 ELUM을 '
            '구현했습니다. 외부 AI로 개인정보가 전달되는 것을 최소화하기 위해 로컬 LLM 기반 '
            '개인정보 탐지·마스킹 계층을 설계했습니다.'
        ),
        period='2026.07.21 — 2026.07.22',
        order=1,
    )
    Activity.objects.create(
        name='Autory · 세종대 자동차제작 동아리',
        description='자동차 제작 및 디지털 제어 파트로 활동하며 2022 대학생 스마트 e모빌리티 경진대회에 출전했습니다.',
        period='2022 — 2023',
        order=2,
    )


def remove_seeded_awards_and_activities(apps, schema_editor) -> None:
    Career = apps.get_model('profile', 'Career')
    Activity = apps.get_model('profile', 'Activity')

    Career.objects.filter(
        category='award',
        organization__in=['제4회 문화체육관광 인공지능·데이터 활용 공모전', '세종대학교'],
        role__in=['문화데이터 우수사례 부문 장려상', '성적우수장학금'],
    ).delete()
    Activity.objects.filter(
        name__in=[
            'AROM Spring Boot 심화반 · Lead Mentor',
            'CODEGATE AI-Start-Up Hackathon',
            'Autory · 세종대 자동차제작 동아리',
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0004_remove_certification_credential_number_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_awards_and_activities, remove_seeded_awards_and_activities),
    ]
