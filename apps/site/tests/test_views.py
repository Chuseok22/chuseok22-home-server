import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_페이지는_home_page_바디_클래스를_사용한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'class="min-h-screen home-page"' in body


@pytest.mark.django_db
def test_프로젝트_페이지는_기본_바디_클래스를_유지한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'class="min-h-screen bg-base-100 text-base-content"' in body


@pytest.mark.django_db
def test_home_페이지_200_응답() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))

    assert response.status_code == 200
    assert response.context['profile'] is None


@pytest.mark.django_db
def test_home_은_profile_이름과_bio를_렌더링한다() -> None:
    from django.test import Client

    from apps.profile.models import Profile

    Profile.objects.create(name='백지훈', tagline='백엔드 개발자', bio='**굵게** 소개')

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '백지훈' in body
    assert '<strong>굵게</strong>' in body


@pytest.mark.django_db
def test_home_은_프로필_이름에_하이라이트_마커를_적용한다() -> None:
    from django.test import Client

    from apps.profile.models import Profile

    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<mark class="home-hl">백지훈</mark>' in body
    assert 'class="home-rule"' in body


@pytest.mark.django_db
def test_home_은_tagline의_줄바꿈을_br로_렌더링한다() -> None:
    from django.test import Client

    from apps.profile.models import Profile

    Profile.objects.create(
        name='백지훈',
        tagline='A full-stack developer.\n기능 구현을 넘어 서비스를 개선하는 풀스택 개발자',
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'A full-stack developer.<br>기능 구현을 넘어 서비스를 개선하는 풀스택 개발자' in body




@pytest.mark.django_db
def test_home_은_star_통계가_없으면_0을_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))

    assert response.context['total_stars'] == 0


@pytest.mark.django_db
def test_home_은_총_star_수를_context에_담는다() -> None:
    from django.test import Client

    from apps.activity.models import GithubProfileStats

    GithubProfileStats.objects.create(pk=1, total_stars=8)

    client = Client()
    response = client.get(reverse('site:home'))

    assert response.context['total_stars'] == 8


@pytest.mark.django_db
def test_home_은_호출마다_방문자_수를_증가시킨다() -> None:
    from django.test import Client

    from apps.profile.models import VisitorCounter

    client = Client()
    client.get(reverse('site:home'))
    client.get(reverse('site:home'))

    assert VisitorCounter.objects.get(pk=1).count == 2


@pytest.mark.django_db
def test_home_은_카테고리별로_기술스택을_그룹핑한다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)
    Skill.objects.create(category=Skill.Category.BACKEND, name='DRF', order=1)
    Skill.objects.create(category=Skill.Category.FRONTEND, name='React', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    grouped = response.context['skills_by_category']

    assert [s.name for s in grouped['backend']] == ['Django', 'DRF']
    assert [s.name for s in grouped['frontend']] == ['React']


@pytest.mark.django_db
def test_home_템플릿은_기술스택_섹션에_eyebrow_라벨을_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="eyebrow">Stack</span>' in body


@pytest.mark.django_db
def test_home_템플릿은_이력_섹션에_eyebrow_라벨을_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='회사', role='개발자',
        period_start=timezone.localdate(), order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="eyebrow">History</span>' in body


@pytest.mark.django_db
def test_home_템플릿은_기술스택_슬러그를_simple_icons_cdn_url로_렌더링한다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', icon_slug='django', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'src="https://cdn.simpleicons.org/django"' in body


@pytest.mark.django_db
def test_home_템플릿은_icon_slug가_완전한_url이면_그대로_렌더링한다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    icon_url = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg'
    Skill.objects.create(category=Skill.Category.BACKEND, name='Java', icon_slug=icon_url, order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert f'src="{icon_url}"' in body


@pytest.mark.django_db
def test_home_은_기술스택_카테고리를_정의_순서대로_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.ETC, name='기타툴', order=0)
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)
    Skill.objects.create(category=Skill.Category.DATABASE, name='PostgreSQL', order=0)
    Skill.objects.create(category=Skill.Category.FRONTEND, name='React', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    categories = list(response.context['skills_by_category'].keys())

    assert categories == ['backend', 'frontend', 'database', 'etc']


@pytest.mark.django_db
def test_home_은_기술스택_카테고리에_Mobile과_AI를_포함한다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.MOBILE, name='Capacitor', order=0)
    Skill.objects.create(category=Skill.Category.AI, name='Gemini', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    categories = list(response.context['skills_by_category'].keys())

    assert 'mobile' in categories
    assert 'ai' in categories
    assert categories.index('mobile') < categories.index('ai')


@pytest.mark.django_db
def test_home_은_is_featured인_프로젝트만_대표_프로젝트로_전달한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=category, title='대표작', description='설명', status=status,
        order=0, is_featured=True,
    )
    Project.objects.create(
        category=category, title='일반작', description='설명', status=status,
        order=1, is_featured=False,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    featured = list(response.context['featured_projects'])

    assert [p.title for p in featured] == ['대표작']


@pytest.mark.django_db
def test_home_은_is_featured_프로젝트를_order_순으로_개수_제한_없이_전달한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    for i in range(5):
        Project.objects.create(
            category=category, title=f'대표작 {i}', description='설명', status=status,
            order=i, is_featured=True,
        )

    client = Client()
    response = client.get(reverse('site:home'))
    featured = list(response.context['featured_projects'])

    assert len(featured) == 5
    assert [p.title for p in featured] == [f'대표작 {i}' for i in range(5)]


@pytest.mark.django_db
def test_home_은_발행된_블로그_글_3개까지_전달한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    for i in range(5):
        Post.objects.create(
            title=f'글 {i}', slug=f'post-{i}', summary='요약', content='본문',
            is_published=True, published_at=timezone.now() - timezone.timedelta(days=i),
        )
    Post.objects.create(
        title='비공개 글', slug='draft', summary='요약', content='본문', is_published=False,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    recent_posts = list(response.context['recent_posts'])

    assert len(recent_posts) == 3
    assert all(p.is_published for p in recent_posts)


@pytest.mark.django_db
def test_projects_페이지는_카테고리별_프로젝트를_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    Project.objects.create(
        category=ProjectCategory.objects.get(name='사이드 프로젝트'),
        title='개인 홈서버',
        description='Django 홈서버',
        status=ProjectStatus.objects.get(name='진행중'),
    )

    client = Client()
    response = client.get(reverse('site:projects'))

    assert response.status_code == 200
    assert '개인 홈서버' in response.content.decode()


@pytest.mark.django_db
def test_projects_페이지는_카테고리_미선택_시_카테고리별로_그룹핑되어_보인다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    team = ProjectCategory.objects.get(name='팀 프로젝트')
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=team, title='팀 프로젝트 A', description='설명', status=status)
    Project.objects.create(category=side, title='사이드 프로젝트 A', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '팀 프로젝트 A' in body
    assert '사이드 프로젝트 A' in body
    # 카테고리명 자체는 사이드바에도 나타나 순서 검증에 부적합하므로, 사이드바에는 없는
    # 프로젝트 제목으로 본문 그룹핑 순서(팀 프로젝트 섹션이 사이드 프로젝트 섹션보다 먼저)를 검증한다.
    assert body.index('팀 프로젝트 A') < body.index('사이드 프로젝트 A')


@pytest.mark.django_db
def test_projects_페이지는_category_파라미터로_해당_카테고리만_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    team = ProjectCategory.objects.get(name='팀 프로젝트')
    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=team, title='팀 프로젝트 전용', description='설명', status=status)
    Project.objects.create(category=side, title='사이드 프로젝트 전용', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'), {'category': side.id})
    body = response.content.decode()

    assert response.status_code == 200
    assert '사이드 프로젝트 전용' in body
    assert '팀 프로젝트 전용' not in body


@pytest.mark.django_db
def test_projects_페이지는_존재하지_않는_category_id면_빈_결과를_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드 프로젝트 전용', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'), {'category': 999999})
    body = response.content.decode()

    assert response.status_code == 200
    assert '사이드 프로젝트 전용' not in body
    assert '등록된 프로젝트가 없습니다' in body


@pytest.mark.django_db
def test_projects_페이지는_비정수_category_값이면_전체를_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드 프로젝트 전용', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'), {'category': 'abc'})
    body = response.content.decode()

    assert response.status_code == 200
    assert '사이드 프로젝트 전용' in body


@pytest.mark.django_db
def test_projects_페이지는_비십진_유니코드_숫자_category_값이면_500_없이_전체를_보여준다() -> None:
    # '²'.isdigit()은 True지만 int('²')는 ValueError를 던진다. isdecimal()만
    # 순수 10진 문자열을 걸러내므로, isdigit()을 썼다면 이 요청이 500 에러가 난다.
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드 프로젝트 전용', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'), {'category': '²'})
    body = response.content.decode()

    assert response.status_code == 200
    assert '사이드 프로젝트 전용' in body


@pytest.mark.django_db
def test_projects_페이지는_HX_Request_헤더가_있으면_프래그먼트만_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:projects'), HTTP_HX_REQUEST='true')
    body = response.content.decode()

    assert response.status_code == 200
    assert '<header' not in body
    assert 'id="projects-content"' in body


@pytest.mark.django_db
def test_projects_페이지는_HX_Request_헤더가_없으면_전체_페이지를_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '<header' in body
    assert 'id="projects-content"' in body


@pytest.mark.django_db
def test_projects_페이지는_HX_History_Restore_Request면_전체_페이지를_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(
        reverse('site:projects'),
        HTTP_HX_REQUEST='true',
        HTTP_HX_HISTORY_RESTORE_REQUEST='true',
    )
    body = response.content.decode()

    assert '<header' in body


@pytest.mark.django_db
def test_project_card는_highlights가_없으면_더보기_버튼을_보여주지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='하이라이트 없음', description='설명', status=status, highlights=[],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '더보기' not in body


@pytest.mark.django_db
def test_project_card는_highlights가_있으면_더보기_버튼을_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='하이라이트 있음', description='설명', status=status,
        highlights=['첫 번째 성과'],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '더보기' in body
    assert '첫 번째 성과' in body
    assert 'aria-expanded' in body


@pytest.mark.django_db
def test_project_card는_title_href가_있으면_제목을_링크로_렌더링한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='링크형 제목', description='설명', status=status,
        title_href='https://example.com/project',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '<a href="https://example.com/project"' in body
    assert '링크형 제목' in body


@pytest.mark.django_db
def test_project_card는_title_href가_없으면_제목이_일반_텍스트다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='일반 제목', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '<h2 class="card-title">일반 제목</h2>' in body


@pytest.mark.django_db
def test_project_card는_기간_역할_인원_링크를_모두_노출한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='상세 정보 전체 노출', description='설명', status=status,
        period='2026.01 ~ 2026.03', role='백엔드', team_size=3,
        github_href='https://github.com/example/repo',
        web_site_href='https://example.com',
        ios_href='https://apps.apple.com/app/id123456789',
        android_href='https://play.google.com/store/apps/details?id=com.example.app',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '2026.01 ~ 2026.03' in body
    assert '백엔드 · 3명' in body
    assert 'https://github.com/example/repo' in body
    assert 'aria-label="GitHub 저장소"' in body
    assert 'https://example.com' in body
    assert 'aria-label="웹사이트"' in body
    assert 'https://apps.apple.com/app/id123456789' in body
    assert 'aria-label="App Store"' in body
    assert 'https://play.google.com/store/apps/details?id=com.example.app' in body
    assert 'aria-label="Google Play"' in body


@pytest.mark.django_db
def test_project_card는_상세_정보가_모두_비면_푸터를_렌더링하지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='상세 정보 없음', description='설명', status=status,
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'divider' not in body
    assert 'aria-label="웹사이트"' not in body


@pytest.mark.django_db
def test_project_card는_ios_href가_없으면_App_Store_아이콘을_보여주지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='iOS 링크 없음', description='설명', status=status,
        android_href='https://play.google.com/store/apps/details?id=com.example.app',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'aria-label="Google Play"' in body
    assert 'aria-label="App Store"' not in body


@pytest.mark.django_db
def test_project_card는_android_href가_없으면_Google_Play_아이콘을_보여주지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='Android 링크 없음', description='설명', status=status,
        ios_href='https://apps.apple.com/app/id123456789',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'aria-label="App Store"' in body
    assert 'aria-label="Google Play"' not in body


@pytest.mark.django_db
def test_project_card는_extra_links를_모두_렌더링한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='기타 링크 노출', description='설명', status=status,
        extra_links=[
            {'label': 'Notion', 'url': 'https://notion.so/example'},
            {'label': '발표자료', 'url': 'https://speakerdeck.com/example'},
        ],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '<a href="https://notion.so/example"' in body
    assert 'Notion' in body
    assert '<a href="https://speakerdeck.com/example"' in body
    assert '발표자료' in body


@pytest.mark.django_db
def test_project_card는_stats가_없으면_통계_표를_보여주지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='통계 없음', description='설명', status=status, stats=[],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'class="stat-table"' not in body


@pytest.mark.django_db
def test_project_card는_stats가_있으면_라벨과_값을_표로_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='통계 있음', description='설명', status=status,
        stats=[
            {'label': '👥 회원', 'value': '136명'},
            {'label': '📦 등록 물품', 'value': '157개'},
        ],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'class="stat-table"' in body
    assert '<td>👥 회원</td><td>136명</td>' in body
    assert '<td>📦 등록 물품</td><td>157개</td>' in body


@pytest.mark.django_db
def test_project_card는_역할_인원_기간을_한_줄로_결합해서_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='메타 결합 테스트', description='설명', status=status,
        role='Backend Lead', team_size=7, period='약 1년 6개월',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '약 1년 6개월 · Backend Lead · 7명' in body


@pytest.mark.django_db
def test_project_card는_메타_정보만_있고_링크가_없으면_구분선을_보여주지_않는다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=side, title='링크 없음', description='설명', status=status,
        role='Backend Lead', team_size=7, period='약 1년 6개월',
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert 'Backend Lead · 7명' in body
    assert 'divider' not in body


@pytest.mark.django_db
def test_projects_사이드바는_프로젝트가_없는_카테고리를_제외한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    side = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(category=side, title='사이드 프로젝트 전용', description='설명', status=status)

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '사이드 프로젝트 (1)' in body
    assert '팀 프로젝트 (' not in body
    assert '오픈소스 (' not in body


@pytest.mark.django_db
def test_blog_목록은_공개된_포스트만_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='공개 글', slug='public-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(title='비공개 글', slug='draft-post', content='본문', is_published=False)

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '공개 글' in body
    assert '비공개 글' not in body


@pytest.mark.django_db
def test_blog_목록은_category_파라미터로_소분류_글만_필터링한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='dev-post', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(
        title='소분류 글', slug='child-post', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': 'waitee-app'})
    body = response.content.decode()

    assert response.status_code == 200
    assert '소분류 글' in body
    assert '대분류 글' not in body


@pytest.mark.django_db
def test_blog_목록은_대분류_slug로_필터링하면_소분류_글도_포함한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    parent = Category.objects.create(name='개발', slug='dev')
    child = Category.objects.create(name='waitee-app', slug='waitee-app', parent=parent)
    Post.objects.create(
        title='대분류 글', slug='dev-post', content='본문', category=parent,
        is_published=True, published_at=timezone.now(),
    )
    Post.objects.create(
        title='소분류 글', slug='child-post', content='본문', category=child,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': 'dev'})
    body = response.content.decode()

    assert '대분류 글' in body
    assert '소분류 글' in body


@pytest.mark.django_db
def test_blog_목록은_존재하지_않는_카테고리면_빈_목록과_200을_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': '없는-슬러그'})

    assert response.status_code == 200
    assert '등록된 글이 없습니다.' in response.content.decode()


@pytest.mark.django_db
def test_blog_목록_context에_사이드바_항목과_전체_글_개수가_담긴다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=category,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))

    assert response.context['total_post_count'] == 1
    assert len(response.context['sidebar_items']) == 1
    assert response.context['sidebar_items'][0].slug == 'dev'
    assert response.context['selected_category_slug'] is None


@pytest.mark.django_db
def test_blog_목록에_카테고리_사이드바가_표시된다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=category,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '개발 (1)' in body
    assert '전체 (1)' in body


@pytest.mark.django_db
def test_HX_Request_헤더가_있으면_프래그먼트만_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'), HTTP_HX_REQUEST='true')
    body = response.content.decode()

    assert response.status_code == 200
    assert '<header' not in body
    assert 'id="blog-content"' in body


@pytest.mark.django_db
def test_HX_Request_헤더가_없으면_전체_페이지를_반환한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '<header' in body
    assert 'id="blog-content"' in body


@pytest.mark.django_db
def test_HX_History_Restore_Request면_HX_Request가_있어도_전체_페이지를_반환한다() -> None:
    """htmx 히스토리 캐시 미스로 인한 재요청은 HX-Request와 HX-History-Restore-Request가
    함께 붙어 오며, 이 경우 htmx는 풀 페이지 응답을 기대한다."""
    from django.test import Client

    client = Client()
    response = client.get(
        reverse('site:blog-list'),
        HTTP_HX_REQUEST='true',
        HTTP_HX_HISTORY_RESTORE_REQUEST='true',
    )
    body = response.content.decode()

    assert '<header' in body


@pytest.mark.django_db
def test_blog_상세는_마크다운을_HTML로_렌더링한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='마크다운 글', slug='markdown-post', content='# 제목입니다',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'markdown-post'}))

    assert response.status_code == 200
    assert '<h1>제목입니다</h1>' in response.content.decode()


@pytest.mark.django_db
def test_비공개_포스트_상세는_404() -> None:
    from django.test import Client

    from apps.blog.models import Post

    Post.objects.create(title='비공개 글', slug='draft-post', content='본문', is_published=False)

    client = Client()
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'draft-post'}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_블로그_수정은_미인증_사용자에게_403() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='원본 제목', slug='edit-target', content='원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.post(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target'}), {
        'title': '새 제목', 'summary': '', 'content': '새 본문',
    })

    assert response.status_code == 403


@pytest.mark.django_db
def test_is_staff_아닌_로그인_사용자는_블로그_수정이_403() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    guest = User.objects.create_user(username='guest', is_staff=False)
    Post.objects.create(
        title='원본 제목', slug='edit-target-guest', content='원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(guest)
    response = client.post(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target-guest'}), {
        'title': '새 제목', 'summary': '', 'content': '새 본문',
    })

    assert response.status_code == 403


@pytest.mark.django_db
def test_소유자는_블로그_글을_수정할_수_있다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(
        title='원본 제목', slug='edit-target-owner', content='원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(owner)
    response = client.post(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target-owner'}), {
        'title': '수정된 제목', 'summary': '수정된 요약', 'content': '수정된 본문',
    })

    assert response.status_code == 200
    assert response.json() == {'success': True}
    post = Post.objects.get(slug='edit-target-owner')
    assert post.title == '수정된 제목'
    assert post.summary == '수정된 요약'
    assert post.content == '수정된 본문'


@pytest.mark.django_db
def test_블로그_수정은_제목이_비어있으면_400을_반환하고_원본을_유지한다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(
        title='원본 제목', slug='edit-target-invalid', content='원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(owner)
    response = client.post(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target-invalid'}), {
        'title': '', 'summary': '', 'content': '수정된 본문',
    })

    assert response.status_code == 400
    data = response.json()
    assert data['success'] is False
    assert 'title' in data['errors']
    post = Post.objects.get(slug='edit-target-invalid')
    assert post.title == '원본 제목'


@pytest.mark.django_db
def test_블로그_수정은_GET_요청을_거부한다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(
        title='원본 제목', slug='edit-target-get', content='원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(owner)
    response = client.get(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target-get'}))

    assert response.status_code == 405


@pytest.mark.django_db
def test_블로그_수정은_비공개_글이면_404() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client

    from apps.blog.models import Post

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(title='비공개 글', slug='edit-target-draft', content='본문', is_published=False)

    client = Client()
    client.force_login(owner)
    response = client.post(reverse('site:blog-post-edit', kwargs={'slug': 'edit-target-draft'}), {
        'title': '새 제목', 'summary': '', 'content': '새 본문',
    })

    assert response.status_code == 404


@pytest.mark.django_db
def test_블로그_이미지_업로드는_미인증_사용자에게_403() -> None:
    from django.test import Client

    client = Client()
    response = client.post(reverse('site:blog-post-upload-image'), {})

    assert response.status_code == 403


@pytest.mark.django_db
def test_is_staff_아닌_로그인_사용자는_블로그_이미지_업로드가_403() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client

    User = get_user_model()
    guest = User.objects.create_user(username='guest', is_staff=False)

    client = Client()
    client.force_login(guest)
    response = client.post(reverse('site:blog-post-upload-image'), {})

    assert response.status_code == 403


@pytest.mark.django_db
def test_소유자는_블로그_이미지를_업로드하고_마크다운을_응답받는다(settings, tmp_path) -> None:
    import io

    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from PIL import Image

    settings.MEDIA_ROOT = tmp_path
    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)

    buffer = io.BytesIO()
    Image.new('RGB', (5, 5), color='blue').save(buffer, format='PNG')
    buffer.seek(0)
    upload = SimpleUploadedFile('photo.png', buffer.read(), content_type='image/png')

    client = Client()
    client.force_login(owner)
    response = client.post(reverse('site:blog-post-upload-image'), {'file': upload})

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['url'].endswith('.webp')
    assert '![업로드 이미지]' in data['markdown']


@pytest.mark.django_db
def test_블로그_이미지_업로드는_파일이_없으면_400을_반환한다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)

    client = Client()
    client.force_login(owner)
    response = client.post(reverse('site:blog-post-upload-image'), {})

    assert response.status_code == 400
    assert response.json()['success'] is False


@pytest.mark.django_db
def test_lab_목록은_소유자전용_도구를_잠금_표시한다() -> None:
    from django.test import Client

    from apps.site.models import Tool

    # slug='library'는 Task 9 시드 마이그레이션(0002_seed_tools)이 이미 사용하므로 충돌을 피하기 위해 별도 slug 사용
    Tool.objects.create(
        title='스터디룸 예약', slug='library-lock-test', description='학술정보원 스터디룸 예약',
        is_owner_only=True, url_name='site:lab-library-placeholder',
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '스터디룸 예약' in body
    assert '소유자 전용' in body  # 잠금 카드 문구만 확인, 링크는 렌더링되지 않음(잠금 분기에서 {% url %} 자체를 호출하지 않음)


@pytest.mark.django_db
def test_lab_목록은_소유자에게_실제_링크를_보여준다() -> None:
    from django.contrib.auth import get_user_model

    from apps.site.models import Tool

    # slug='library'는 Task 9 시드 마이그레이션(0002_seed_tools)이 이미 사용하므로 충돌을 피하기 위해 별도 slug 사용
    Tool.objects.create(
        title='스터디룸 예약', slug='library-link-test', description='학술정보원 스터디룸 예약',
        is_owner_only=True, url_name='site:lab-library',
    )

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)

    from django.test import Client

    client = Client()
    client.force_login(owner)
    response = client.get(reverse('site:lab-index'))

    assert 'href="/lab/library/"' in response.content.decode()


@pytest.mark.django_db
def test_시드된_Tool은_소유자에게_두_링크_모두_보여준다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    client = Client()
    client.force_login(owner)

    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'href="/lab/library/"' in body
    assert 'href="/lab/student/"' in body




@pytest.mark.django_db
def test_home_템플릿은_총_star_수를_gh_star로_보여준다() -> None:
    from django.test import Client

    from apps.activity.models import GithubProfileStats

    GithubProfileStats.objects.create(pk=1, total_stars=8)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="gh-star">' in body
    assert '<span class="icon">★</span>8' in body


@pytest.mark.django_db
def test_home_템플릿은_더_이상_방문자_수를_보여주지_않는다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'stat-chip' not in body
    # eye.svg.html은 include된 SVG 내용이 그대로 인라인되므로 파일명이 아니라
    # 아이콘 고유 path 데이터(M2.036 12.322...)로 부재를 검증해야 실제로 의미 있는 검증이 된다.
    # ('eye.svg' not in body'는 애초에 파일명이 출력에 등장하지 않으므로 항상 통과하는 무의미한 assert였다.)
    assert 'M2.036 12.322' not in body


@pytest.mark.django_db
def test_blog_목록은_포스트의_태그를_배지로_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post, Tag

    post = Post.objects.create(
        title='태그 글', slug='tag-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )
    post.tags.add(Tag.objects.create(name='Django', slug='django'))
    post.tags.add(Tag.objects.create(name='React', slug='react'))

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert 'Django' in body
    assert 'React' in body


@pytest.mark.django_db
def test_blog_상세는_포스트의_태그를_배지로_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post, Tag

    post = Post.objects.create(
        title='태그 상세 글', slug='tag-detail-post', content='# 본문',
        is_published=True, published_at=timezone.now(),
    )
    post.tags.add(Tag.objects.create(name='Django', slug='django'))

    client = Client()
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'tag-detail-post'}))
    body = response.content.decode()

    assert 'Django' in body


@pytest.mark.django_db
def test_blog_목록은_태그가_없는_포스트에_배지_블록을_렌더링하지_않는다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='태그 없는 글', slug='no-tag-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert 'badge' not in body


@pytest.mark.django_db
def test_블로그_상세는_태그를_파스텔_배지_스타일로_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post, Tag

    post = Post.objects.create(
        title='파스텔 태그 글', slug='pastel-tag-post', content='# 본문',
        is_published=True, published_at=timezone.now(),
    )
    post.tags.add(Tag.objects.create(name='Django', slug='django'))

    client = Client()
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'pastel-tag-post'}))
    body = response.content.decode()

    assert '<span class="badge-tag">Django</span>' in body


@pytest.mark.django_db
def test_블로그_목록은_태그를_파스텔_배지_스타일로_보여주고_본문과_간격을_둔다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post, Tag

    post = Post.objects.create(
        title='파스텔 태그 목록 글', slug='pastel-tag-list-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )
    post.tags.add(Tag.objects.create(name='Django', slug='django'))

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '<div class="not-prose flex gap-2 flex-wrap mt-3">' in body
    assert '<span class="badge-tag">Django</span>' in body


@pytest.mark.django_db
def test_프로젝트_페이지는_태그를_파스텔_배지_스타일로_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    Project.objects.create(
        category=ProjectCategory.objects.get(name='사이드 프로젝트'),
        title='파스텔 태그 프로젝트',
        description='설명',
        status=ProjectStatus.objects.get(name='진행중'),
        tags=['Django', 'DRF'],
    )

    client = Client()
    response = client.get(reverse('site:projects'))
    body = response.content.decode()

    assert '<span class="badge-tag">Django</span>' in body


@pytest.mark.django_db
def test_헤더는_데스크톱_네비게이션과_모바일_햄버거_메뉴를_모두_렌더링한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'hidden md:flex' in body
    assert 'aria-label="메뉴 열기"' in body
    assert 'mobileMenuOpen' in body
    assert ':aria-expanded="mobileMenuOpen' in body


@pytest.mark.django_db
def test_블로그_목록은_모바일용_가로_스크롤_카테고리_바와_데스크톱용_사이드바를_모두_렌더링한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=category,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert 'flex md:hidden gap-2 overflow-x-auto' in body
    assert 'hidden md:block w-48' in body


@pytest.mark.django_db
def test_블로그_목록은_글_목록_컨테이너에_구분선_클래스를_적용한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='글', slug='post-1', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert 'divide-y divide-base-300' in body


@pytest.mark.django_db
def test_blog_detail은_조회할_때마다_조회수를_증가시킨다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='조회수 테스트', slug='view-count-test', content='# 본문', is_published=True,
    )

    client = Client()
    client.get(reverse('site:blog-detail', args=[post.slug]))
    post.refresh_from_db()
    assert post.views_count == 1

    client.get(reverse('site:blog-detail', args=[post.slug]))
    post.refresh_from_db()
    assert post.views_count == 2


@pytest.mark.django_db
def test_blog_detail은_비공개_포스트_조회시_조회수를_증가시키지_않는다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='비공개 글', slug='draft-post', content='# 본문', is_published=False,
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', args=[post.slug]))

    assert response.status_code == 404
    post.refresh_from_db()
    assert post.views_count == 0


@pytest.mark.django_db
def test_blog_detail은_조회수를_화면에_표시한다() -> None:
    import re

    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='조회수 노출 테스트', slug='view-count-display-test', content='# 본문', is_published=True,
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', args=[post.slug]))

    assert re.search(r'<span class="opacity-60 inline-flex items-center gap-1">.*?1</span>', response.content.decode(), re.DOTALL)


@pytest.mark.django_db
def test_blog_list은_각_포스트의_조회수를_표시한다() -> None:
    import re

    from django.test import Client

    from apps.blog.models import Post

    Post.objects.create(
        title='인기 글', slug='popular-post', content='# 본문',
        is_published=True, views_count=5,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))

    assert re.search(r'<p class="opacity-50 text-xs mt-1 flex items-center gap-2">.*?>5</span>', response.content.decode(), re.DOTALL)


@pytest.mark.django_db
def test_blog_list은_htmx_요청에도_조회수를_표시한다() -> None:
    import re

    from django.test import Client

    from apps.blog.models import Post

    Post.objects.create(
        title='인기 글', slug='popular-post-htmx', content='# 본문',
        is_published=True, views_count=7,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), HTTP_HX_REQUEST='true')

    assert re.search(r'<p class="opacity-50 text-xs mt-1 flex items-center gap-2">.*?>7</span>', response.content.decode(), re.DOTALL)


@pytest.mark.django_db
def test_home_템플릿은_대표_PR을_링크와_함께_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import PullRequestHighlight

    PullRequestHighlight.objects.create(
        title='활동 이력 자동 정리 기능', repo_name='chuseok22/chuseok22-home-server',
        pr_url='https://github.com/Chuseok22/chuseok22-home-server/pull/62', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '활동 이력 자동 정리 기능' in body
    assert 'href="https://github.com/Chuseok22/chuseok22-home-server/pull/62"' in body


@pytest.mark.django_db
def test_home_템플릿은_이력의_종료일이_없으면_현재로_표시한다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '추석22' in body
    assert '현재' in body


@pytest.mark.django_db
def test_home_템플릿은_이력을_직장_학력_그룹으로_구분해서_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=0,
    )
    Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2020-03-01', period_end='2026-02-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '직장' in body
    assert '학력' in body
    assert '[직장]' not in body
    assert '[학력]' not in body


@pytest.mark.django_db
def test_home_은_이력_섹션에서_수상_카테고리를_제외한다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='회사', role='개발자',
        period_start='2026-01-01', order=0,
    )
    Career.objects.create(
        category=Career.Category.AWARD, organization='공모전', role='장려상',
        period_start='2026-08-06', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    categories = list(response.context['careers_by_category'].keys())

    assert categories == ['work']


@pytest.mark.django_db
def test_home_은_awards_컨텍스트에_수상_카테고리만_담는다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='회사', role='개발자',
        period_start='2026-01-01', order=0,
    )
    Career.objects.create(
        category=Career.Category.AWARD, organization='테스트 공모전', role='테스트상',
        period_start='2026-08-06', order=99,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    awards = list(response.context['awards'])

    assert all(award.category == 'award' for award in awards)
    assert any(award.organization == '테스트 공모전' for award in awards)


@pytest.mark.django_db
def test_home_템플릿은_awards_섹션에_eyebrow_라벨을_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.AWARD, organization='제4회 문화체육관광 인공지능·데이터 활용 공모전',
        role='문화데이터 우수사례 부문 장려상', period_start='2026-08-06', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="eyebrow">Awards</span>' in body
    assert 'Awards &amp; Honors' in body
    assert '제4회 문화체육관광 인공지능·데이터 활용 공모전' in body
    assert '<mark class="home-hl">문화데이터 우수사례 부문 장려상</mark>' in body
    assert 'class="medal"' in body


@pytest.mark.django_db
def test_home_은_awards가_없으면_Awards_섹션을_렌더링하지_않는다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    # Task 6에서 시딩된 수상 데이터를 지워 "수상 데이터가 전혀 없는" 상태를 만든다
    Career.objects.filter(category=Career.Category.AWARD).delete()

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="eyebrow">Awards</span>' not in body


@pytest.mark.django_db
def test_home_템플릿은_직장_그룹을_학력_그룹보다_먼저_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2020-03-01', period_end='2026-02-01', order=0,
    )
    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert body.index('추석22') < body.index('세종대학교')


@pytest.mark.django_db
def test_home_템플릿은_자격증_카드에_자격증명_취득일_발급기관을_모두_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Certification

    Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '정보처리기사' in body
    assert '2025.01.01' in body
    assert '한국산업인력공단' in body
    assert '한국산업인력공단 · 2025.01.01' not in body


@pytest.mark.django_db
def test_home_템플릿은_배지_이미지가_없는_자격증은_클릭을_비활성화한다() -> None:
    from django.test import Client

    from apps.profile.models import Certification

    cert = Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert f'openId = {cert.id}' not in body


@pytest.mark.django_db
def test_home_템플릿은_배지_이미지가_있는_자격증은_클릭시_이미지_라이트박스로_확대해서_보여준다(settings, tmp_path) -> None:
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from PIL import Image

    from apps.profile.models import Certification

    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    Image.new('RGB', (5, 5), color='blue').save(buffer, format='PNG')
    buffer.seek(0)
    badge_image = SimpleUploadedFile('badge.png', buffer.read(), content_type='image/png')

    cert = Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
        badge_image=badge_image,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert f'openId = {cert.id}' in body
    assert f'src="{cert.badge_image.url}"' in body
    assert '@keydown.escape.window="openId = null"' in body


@pytest.mark.django_db
def test_home_템플릿은_최근_글과_더보기_링크를_사이드바에_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='첫 글', slug='first-post', summary='요약', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '첫 글' in body
    assert body.count(f'href="{reverse("site:blog-list")}"') == 3




@pytest.mark.django_db
def test_홈페이지는_넓어진_컨테이너_폭을_사용한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'max-w-4xl' not in body
    assert body.count('max-w-6xl') == 2


@pytest.mark.django_db
def test_home_은_github_링크_옆에_아이콘을_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Profile

    Profile.objects.create(
        name='백지훈', tagline='백엔드 개발자', github_url='https://github.com/Chuseok22',
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'src="https://cdn.simpleicons.org/github"' in body


@pytest.mark.django_db
def test_home_템플릿은_기술스택을_tag_skill_클래스로_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Skill

    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'class="tag-skill"' in body


@pytest.mark.django_db
def test_home_템플릿은_데이터가_없어도_필수_섹션_박스_2개를_보여준다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    # section-box 2개(GitHub 컨트리뷰션 + 사이드바 최근 글) + 시딩된 데이터로 항상 렌더링되는
    # "활동" 섹션 1개 + "Awards & Honors" 섹션 1개 = 4개.
    assert body.count('class="section-box') == 4


@pytest.mark.django_db
def test_home_템플릿은_프로필과_기술스택_섹션도_박스로_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Profile, Skill

    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert body.count('class="section-box') == 6


@pytest.mark.django_db
def test_home_페이지는_전역_페이지_전환_진행바_마크업을_포함한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'id="page-loading-bar"' in body
    assert 'site/js/page-loading.js' in body


@pytest.mark.django_db
def test_blog_목록_HTMX_응답은_스켈레톤_인디케이터와_전환_속성을_포함한다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'), HTTP_HX_REQUEST='true')
    body = response.content.decode()

    assert 'data-page-transition' in body
    assert 'hx-indicator="#blog-list-skeleton"' in body
    assert 'id="blog-list-skeleton"' in body


@pytest.mark.django_db
def test_blog_목록_전체_페이지는_aria_live_영역이_blog_content_바깥에_있다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    aria_live_index = body.index('<div aria-live="polite">')
    blog_content_index = body.index('id="blog-content"')

    assert aria_live_index < blog_content_index
    assert 'aria-live="polite"' not in body[body.index('id="blog-content"'):body.index('id="blog-content"') + 500]


@pytest.mark.django_db
def test_블로그_상세는_댓글_폼에_요청_중_비활성화_속성과_스피너를_포함한다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    user = User.objects.create_user(username='reader')
    Post.objects.create(
        title='댓글 테스트 글', slug='comment-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(user)
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'comment-post'}))
    body = response.content.decode()

    assert 'hx-disabled-elt="find button"' in body
    assert 'id="comments" aria-live="polite"' in body


@pytest.mark.django_db
def test_자격증_라이트박스는_이미지_로딩_전_스켈레톤을_보여준다(settings, tmp_path) -> None:
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from PIL import Image

    from apps.profile.models import Certification

    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    Image.new('RGB', (5, 5), color='blue').save(buffer, format='PNG')
    buffer.seek(0)
    badge_image = SimpleUploadedFile('badge.png', buffer.read(), content_type='image/png')

    Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
        badge_image=badge_image,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'x-data="{ loaded: false }"' in body
    assert 'x-init="if ($el.complete) loaded = true"' in body
    assert '@load="loaded = true"' in body
    assert 'skeleton' in body


@pytest.mark.django_db
def test_home_은_아바타를_112px_둥근_정사각형으로_렌더링한다(settings, tmp_path) -> None:
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from PIL import Image

    from apps.profile.models import Profile

    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buffer, format='PNG')
    buffer.seek(0)
    avatar = SimpleUploadedFile('avatar.png', buffer.read(), content_type='image/png')
    Profile.objects.create(name='백지훈', tagline='백엔드 개발자', avatar=avatar)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'w-28 h-28 rounded-xl object-cover' in body


@pytest.mark.django_db
def test_lab_index는_알리미_카드와_discord_cta를_렌더링한다() -> None:
    from django.test import Client, override_settings

    from apps.core.models import ScheduledJobConfig
    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='세종대 학사공지',
        url='https://www.sejong.ac.kr/kor/intro/notice3.do',
        crawler_type='sejong',
        description='세종대학교 학사공지를 자동으로 수집해 알려드립니다.',
        discord_webhook_url='https://discord.com/api/webhooks/1/a',
        is_active=True,
    )
    NoticeSource.objects.create(
        name='중단된 소스',
        url='https://example.com',
        crawler_type='dacon',
        description='',
        # 한때 Discord에 연동됐다가 지금은 비활성화된 소스를 나타낸다(웹훅 없는 소스는
        # lab_index 쿼리셋에서 애초에 제외되므로, "중단됨" 배지를 검증하려면 웹훅이 있어야 한다).
        discord_webhook_url='https://discord.com/api/webhooks/2/inactive',
        is_active=False,
    )
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices',
        is_enabled=True,
        cron_day_of_week='*',
        schedule_mode='fixed_times',
        fixed_hours='8',
        fixed_minute=0,
    )

    with override_settings(DISCORD_INVITE_URL='https://discord.gg/test-invite'):
        client = Client()
        response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '세종대 학사공지' in body
    assert '세종대학교 학사공지를 자동으로 수집해 알려드립니다.' in body
    assert '중단된 소스' in body
    assert '운영 중' in body
    assert '중단됨' in body
    assert '08:00' in body
    assert 'https://discord.gg/test-invite' in body


@pytest.mark.django_db
def test_lab_index는_github_trending_소스에_전용_스케줄러_잡의_일정을_표시한다() -> None:
    """github_trending 소스는 check_new_notices가 아니라 send_github_trending_report 잡으로
    운영되므로, 두 ScheduledJobConfig의 스케줄이 다를 때 카드마다 각자의 실제 잡 일정을
    표시하는지 검증한다(Finding 2 회귀 테스트)."""
    from django.test import Client

    from apps.core.models import ScheduledJobConfig
    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='세종대 학사공지',
        url='https://www.sejong.ac.kr/kor/intro/notice3.do',
        crawler_type='sejong',
        description='',
        discord_webhook_url='https://discord.com/api/webhooks/1/a',
        is_active=True,
    )
    NoticeSource.objects.create(
        name='GitHub 트렌딩 리포트',
        url='https://github.com/trending?since=daily',
        crawler_type='github_trending',
        description='',
        discord_webhook_url='https://discord.com/api/webhooks/2/b',
        is_active=True,
    )
    ScheduledJobConfig.objects.create(
        job_id='check_new_notices',
        is_enabled=True,
        cron_day_of_week='*',
        schedule_mode='fixed_times',
        fixed_hours='8',
        fixed_minute=0,
    )
    ScheduledJobConfig.objects.create(
        job_id='send_github_trending_report',
        is_enabled=True,
        cron_day_of_week='*',
        schedule_mode='fixed_times',
        fixed_hours='9',
        fixed_minute=0,
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '08:00' in body
    assert '09:00' in body

    sejong_source = next(s for s in response.context['notice_sources'] if s.name == '세종대 학사공지')
    github_source = next(s for s in response.context['notice_sources'] if s.name == 'GitHub 트렌딩 리포트')
    assert sejong_source.schedule_text == '매일 08:00 자동 수집'
    assert github_source.schedule_text == '매일 09:00 자동 수집'


@pytest.mark.django_db
def test_lab_index는_discord_invite_url_미설정시_cta만_숨긴다() -> None:
    from django.test import Client, override_settings

    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='세종대 학사공지',
        url='https://www.sejong.ac.kr/kor/intro/notice3.do',
        crawler_type='sejong',
        description='',
        # lab_index가 discord_webhook_url이 설정된 소스만 노출하므로, 이 소스가
        # 본문에 나타나려면 웹훅이 있어야 한다(CTA 숨김 여부와는 별개 검증 대상).
        discord_webhook_url='https://discord.com/api/webhooks/3/active',
        is_active=True,
    )

    with override_settings(DISCORD_INVITE_URL=''):
        client = Client()
        response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '세종대 학사공지' in body
    assert 'Discord 참여 신청' not in body


@pytest.mark.django_db
def test_lab_index는_discord_webhook_미설정_소스를_노출하지_않는다() -> None:
    """discord_webhook_url이 빈 소스는 is_active=True여도 check_new_notices가 발송을
    건너뛰므로 실제로는 운영 중이 아니다. lab 페이지가 이런 소스를 "운영 중"으로 잘못
    노출하지 않는지 검증한다(Finding 1 회귀 테스트)."""
    from django.test import Client

    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='웹훅_미설정_소스',
        url='https://example.com',
        crawler_type='dacon',
        description='',
        discord_webhook_url='',
        is_active=True,
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '웹훅_미설정_소스' not in body


class TestFormatNoticeScheduleText:
    """apps.site.views._format_notice_schedule_text의 분기별 동작을 검증한다."""

    def test_config_none이면_미설정_문구(self) -> None:
        from apps.site.views import _format_notice_schedule_text

        assert _format_notice_schedule_text(None) == '자동 수집 일정 미설정'

    def test_interval_모드(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='interval', interval_hours=3, interval_minute=0,
            cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '매일 3시간마다 자동 수집'

    def test_interval_24시간은_매일_자동_수집(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='interval', interval_hours=24, interval_minute=0,
            cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '매일 자동 수집'

    def test_interval_hours_none이어도_예외없이_기본_문구(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='interval', interval_hours=None, interval_minute=0,
            cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '매일 자동 수집'

    def test_특정_요일_여러개(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='fixed_times', fixed_hours='9', fixed_minute=30,
            cron_day_of_week='mon,wed',
        )
        assert _format_notice_schedule_text(config) == '매주 월요일, 수요일 09:30 자동 수집'

    def test_알수없는_요일_토큰이어도_예외없이_토큰_그대로_사용(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='fixed_times', fixed_hours='9', fixed_minute=0,
            cron_day_of_week='invalid',
        )
        assert _format_notice_schedule_text(config) == '매주 invalid 09:00 자동 수집'

    def test_is_enabled_false면_중단_문구(self) -> None:
        """잡이 꺼져 있으면(운영자가 자동화 제어 화면에서 비활성화) 실제로 수집이 멈춘 상태이므로
        공개 페이지에 여전히 "매일 08:00 자동 수집"처럼 동작 중인 것처럼 보여주면 안 된다."""
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', is_enabled=False, schedule_mode='fixed_times', fixed_hours='8',
            fixed_minute=0, cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '자동 수집 일시 중단'

    def test_fixed_hours에_숫자가_아닌_토큰이_있어도_예외없이_무시(self) -> None:
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='fixed_times', fixed_hours='8,abc', fixed_minute=0,
            cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '매일 08:00 자동 수집'

    def test_fixed_hours에_isdigit은_true지만_int_변환이_실패하는_문자가_있어도_예외없이_무시(self) -> None:
        """'²'(U+00B2)는 str.isdigit()이 True를 반환하지만 int()는 ValueError를 던진다 —
        isdecimal()을 써야 하는 이유를 직접 검증한다(이 프로젝트가 apps/site/views.py의
        projects 뷰에서 이미 겪은 것과 동일한 함정)."""
        from apps.core.models import ScheduledJobConfig
        from apps.site.views import _format_notice_schedule_text

        config = ScheduledJobConfig(
            job_id='x', schedule_mode='fixed_times', fixed_hours='8,²', fixed_minute=0,
            cron_day_of_week='*',
        )
        assert _format_notice_schedule_text(config) == '매일 08:00 자동 수집'


@pytest.mark.django_db
def test_lab_목록은_도구_아이콘이_있으면_렌더링한다() -> None:
    from django.test import Client

    from apps.site.models import Tool

    Tool.objects.create(
        title='아이콘 도구', slug='icon-tool-present', description='설명',
        icon='🧪', url_name='site:lab-library',
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '<span class="text-xl" aria-hidden="true">🧪</span>' in body


@pytest.mark.django_db
def test_lab_목록은_도구_아이콘이_없으면_아이콘_영역을_렌더링하지_않는다() -> None:
    from django.test import Client

    from apps.site.models import Tool

    Tool.objects.create(
        title='아이콘 없는 도구', slug='icon-tool-absent', description='설명',
        icon='', url_name='site:lab-library',
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '아이콘 없는 도구' in body
    assert '<span class="text-xl" aria-hidden="true"></span>' not in body


@pytest.mark.django_db
def test_lab_index는_알리미_아이콘이_있으면_렌더링한다() -> None:
    from django.test import Client

    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='아이콘 소스', url='https://example.com', crawler_type='sejong',
        icon='📌', discord_webhook_url='https://discord.com/api/webhooks/9/a',
        is_active=True,
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '<span class="text-xl" aria-hidden="true">📌</span>' in body


@pytest.mark.django_db
def test_lab_index는_알리미_아이콘이_없으면_아이콘_영역을_렌더링하지_않는다() -> None:
    from django.test import Client

    from apps.notifications.models import NoticeSource

    NoticeSource.objects.create(
        name='아이콘 없는 소스', url='https://example.com', crawler_type='sejong',
        icon='', discord_webhook_url='https://discord.com/api/webhooks/9/b',
        is_active=True,
    )

    client = Client()
    response = client.get(reverse('site:lab-index'))
    body = response.content.decode()

    assert response.status_code == 200
    assert '아이콘 없는 소스' in body
    assert '<span class="text-xl" aria-hidden="true"></span>' not in body


@pytest.mark.django_db
def test_blog_detail은_mermaid_블록이_있으면_has_mermaid를_true로_전달한다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='다이어그램 글', slug='mermaid-post',
        content='# 제목\n\n```mermaid\nflowchart LR\n    A --> B\n```',
        is_published=True,
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', args=[post.slug]))

    assert response.context['has_mermaid'] is True
    assert 'mermaid@' in response.content.decode()


@pytest.mark.django_db
def test_blog_detail은_mermaid_블록이_없으면_has_mermaid를_false로_전달한다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='일반 글', slug='no-mermaid-post', content='# 제목\n\n일반 본문', is_published=True,
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', args=[post.slug]))

    assert response.context['has_mermaid'] is False
    assert 'mermaid@' not in response.content.decode()


@pytest.mark.django_db
def test_blog_detail은_toc_레이아웃과_스크립트를_포함한다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    post = Post.objects.create(
        title='TOC 테스트', slug='toc-test', content='# 제목\n\n본문', is_published=True,
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', args=[post.slug]))
    body = response.content.decode()

    assert 'id="post-toc-desktop-wrapper"' in body
    assert 'id="post-toc-mobile-wrapper"' in body
    assert 'markdown-code-blocks.js' in body
    assert 'blog-post-toc.js' in body


@pytest.mark.django_db
def test_blog_목록은_기본적으로_게시일_내림차순으로_정렬된다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    older = Post.objects.create(
        title='오래된 글', slug='older-post', content='본문',
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=2),
    )
    newer = Post.objects.create(
        title='최신 글', slug='newer-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))

    assert list(response.context['posts']) == [newer, older]
    assert response.context['current_sort'] == 'latest'


@pytest.mark.django_db
def test_blog_목록은_sort_views_파라미터로_조회수_내림차순_정렬한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    low_views = Post.objects.create(
        title='조회수 낮은 글', slug='low-views-post', content='본문',
        is_published=True, published_at=timezone.now(), views_count=1,
    )
    high_views = Post.objects.create(
        title='조회수 높은 글', slug='high-views-post', content='본문',
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=1), views_count=10,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'sort': 'views'})

    assert list(response.context['posts']) == [high_views, low_views]
    assert response.context['current_sort'] == 'views'


@pytest.mark.django_db
def test_blog_목록은_유효하지_않은_sort_값이면_기본_정렬로_폴백한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    older = Post.objects.create(
        title='오래된 글', slug='older-post', content='본문',
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=2),
    )
    newer = Post.objects.create(
        title='최신 글', slug='newer-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'sort': 'foo'})

    assert response.status_code == 200
    assert list(response.context['posts']) == [newer, older]
    assert response.context['current_sort'] == 'latest'


@pytest.mark.django_db
def test_blog_목록은_category와_sort를_함께_적용한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    other_category = Category.objects.create(name='일상', slug='life')

    Post.objects.create(
        title='개발 글 - 조회수 낮음', slug='dev-low', content='본문', category=category,
        is_published=True, published_at=timezone.now(), views_count=1,
    )
    dev_high = Post.objects.create(
        title='개발 글 - 조회수 높음', slug='dev-high', content='본문', category=category,
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=1), views_count=10,
    )
    Post.objects.create(
        title='다른 카테고리 글', slug='life-post', content='본문', category=other_category,
        is_published=True, published_at=timezone.now(), views_count=99,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': 'dev', 'sort': 'views'})
    body = response.content.decode()
    posts = list(response.context['posts'])

    assert '다른 카테고리 글' not in body
    assert posts[0] == dev_high


@pytest.mark.django_db
def test_blog_목록에_게시일이_YYYY_MM_DD_형식으로_표시된다() -> None:
    import datetime as dt

    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='날짜 표시 글', slug='dated-post', content='본문',
        is_published=True,
        published_at=timezone.make_aware(dt.datetime(2026, 8, 1, 12, 0)),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '2026-08-01' in body


@pytest.mark.django_db
def test_blog_목록에_정렬_탭_링크가_표시된다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '최신순' in body
    assert '조회순' in body
    assert 'sort=views' in body


@pytest.mark.django_db
def test_blog_목록은_활성_정렬_탭에_강조_클래스를_적용한다() -> None:
    import re

    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'), {'sort': 'views'})
    body = response.content.decode()

    views_tab_match = re.search(r'class="btn btn-sm ([^"]*)"[^>]*>조회순', body)
    latest_tab_match = re.search(r'class="btn btn-sm ([^"]*)"[^>]*>최신순', body)

    assert views_tab_match is not None and 'btn-primary' in views_tab_match.group(1)
    assert latest_tab_match is not None and 'btn-primary' not in latest_tab_match.group(1)


@pytest.mark.django_db
def test_blog_목록_정렬_탭은_현재_카테고리를_유지한다() -> None:
    import re

    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=category,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': 'dev'})
    body = response.content.decode()

    match = re.search(r'hx-get="([^"]*sort=views[^"]*)"', body)
    assert match is not None
    assert 'category=dev' in match.group(1)


@pytest.mark.django_db
def test_blog_목록_카테고리_링크는_현재_정렬을_유지한다() -> None:
    import re

    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Category, Post

    category = Category.objects.create(name='개발', slug='dev')
    Post.objects.create(
        title='글', slug='post-1', content='본문', category=category,
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-list'), {'sort': 'views'})
    body = response.content.decode()

    match = re.search(r'hx-get="([^"]*category=dev[^"]*)"', body)
    assert match is not None
    assert 'sort=views' in match.group(1)


@pytest.mark.django_db
def test_blog_목록_전체_링크는_카테고리를_제거하되_정렬은_유지한다() -> None:
    import re

    from django.test import Client

    client = Client()
    response = client.get(reverse('site:blog-list'), {'category': 'dev', 'sort': 'views'})
    body = response.content.decode()

    match = re.search(r'hx-get="([^"]*)"[^>]*>전체', body)
    assert match is not None
    assert 'sort=views' in match.group(1)
    assert 'category=dev' not in match.group(1)


@pytest.mark.django_db
def test_blog_목록은_게시일이_없는_공개_글을_최신순_정렬에서_마지막에_배치한다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    dated = Post.objects.create(
        title='날짜 있는 글', slug='dated-post', content='본문',
        is_published=True, published_at=timezone.now() - timezone.timedelta(days=5),
    )
    undated = Post.objects.create(
        title='날짜 없는 글', slug='undated-post', content='본문',
        is_published=True, published_at=None,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    posts = list(response.context['posts'])

    assert posts == [dated, undated]


@pytest.mark.django_db
def test_blog_목록은_게시일이_없는_공개_글의_날짜를_표시하지_않는다() -> None:
    from django.test import Client

    from apps.blog.models import Post

    Post.objects.create(
        title='날짜 없는 글 2', slug='undated-post-2', content='본문',
        is_published=True, published_at=None,
    )

    client = Client()
    response = client.get(reverse('site:blog-list'))
    body = response.content.decode()

    assert '날짜 없는 글 2' in body
    assert '<span></span>' not in body


@pytest.mark.django_db
def test_blog_상세는_소유자에게_수정_UI를_보여준다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    owner = User.objects.create_user(username='owner', is_staff=True)
    Post.objects.create(
        title='원본 제목', slug='owner-view-post', summary='원본 요약', content='# 원본 본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(owner)
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'owner-view-post'}))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'id="post-edit-toggle"' in body
    assert 'id="post-edit-form"' in body
    assert '# 원본 본문' in body  # textarea 안에 원본 마크다운(렌더링 전 원문)이 그대로 있어야 함
    assert f"data-edit-url=\"{reverse('site:blog-post-edit', kwargs={'slug': 'owner-view-post'})}\"" in body
    assert f"data-upload-url=\"{reverse('site:blog-post-upload-image')}\"" in body


@pytest.mark.django_db
def test_blog_상세는_비소유자에게_수정_UI를_숨긴다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    Post.objects.create(
        title='원본 제목', slug='non-owner-view-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'non-owner-view-post'}))
    body = response.content.decode()

    assert 'id="post-edit-toggle"' not in body
    assert 'id="post-edit-form"' not in body


@pytest.mark.django_db
def test_blog_상세는_is_staff_아닌_로그인_사용자에게도_수정_UI를_숨긴다() -> None:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from apps.blog.models import Post

    User = get_user_model()
    guest = User.objects.create_user(username='guest', is_staff=False)
    Post.objects.create(
        title='원본 제목', slug='guest-view-post', content='본문',
        is_published=True, published_at=timezone.now(),
    )

    client = Client()
    client.force_login(guest)
    response = client.get(reverse('site:blog-detail', kwargs={'slug': 'guest-view-post'}))
    body = response.content.decode()

    assert 'id="post-edit-toggle"' not in body


@pytest.mark.django_db
def test_home_프로젝트_섹션은_1열_grid를_사용한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=category, title='대표작', description='설명', status=status,
        is_featured=True,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    # "grid gap-4"는 대표 PR 섹션에도 쓰이므로, 프로젝트 섹션 자체의 마크업만 잘라내 검증한다.
    projects_start = body.index('<span class="eyebrow">Projects</span>')
    projects_section = body[projects_start:body.index('</section>', projects_start)]

    assert 'grid gap-4' in projects_section
    assert 'md:grid-cols-2' not in projects_section
    assert 'items-start' not in projects_section


@pytest.mark.django_db
def test_home_프로젝트_섹션은_project_card_파셜을_재사용한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    Project.objects.create(
        category=category, title='대표작', description='설명', status=status,
        is_featured=True, highlights=['설계 포인트 1'],
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    # project_card.html의 "더보기" 토글은 홈에서도 렌더링돼야 한다
    assert '더보기' in body
    assert '설계 포인트 1' in body


@pytest.mark.django_db
def test_home_은_활동_연도_목록을_내림차순으로_정렬해서_전달한다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.all().delete()
    Activity.objects.create(name='2024년 활동', start_year=2024, order=100)
    Activity.objects.create(name='2022~2023년 활동', start_year=2022, end_year=2023, order=101)

    client = Client()
    response = client.get(reverse('site:home'))

    assert list(response.context['activity_years']) == [2024, 2023, 2022]


@pytest.mark.django_db
def test_home_은_다년도_활동의_연도를_모두_activity_years에_포함한다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.all().delete()
    Activity.objects.create(name='다년도 활동', start_year=2020, end_year=2021, order=100)

    client = Client()
    response = client.get(reverse('site:home'))

    assert response.context['activity_years'] == [2021, 2020]


@pytest.mark.django_db
def test_home_활동_섹션은_이력과_동일한_타임라인_마크업을_사용한다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.create(
        name='AROM Spring Boot 심화반 테스트용', description='설명 테스트',
        period='2099.1학기', start_year=2099, order=100,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<span class="eyebrow">Activities</span>' in body
    assert 'AROM Spring Boot 심화반 테스트용' in body
    assert '2099.1학기' in body
    assert '설명 테스트' in body
    assert '<ul class="flex flex-col gap-4 border-l-2 border-base-300 pl-4">' in body


@pytest.mark.django_db
def test_home_활동_섹션은_연도_세그먼트_필터를_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.all().delete()
    Activity.objects.create(name='필터 테스트 활동', start_year=2025, order=100)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'year-segment-group' in body
    assert '>전체<' in body
    assert '>2025<' in body


@pytest.mark.django_db
def test_home_활동_섹션은_links의_타입별로_아이콘_링크를_렌더링한다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.create(
        name='아이콘 링크 테스트', start_year=2026, order=100,
        links=[{'type': 'github', 'url': 'https://github.com/example'}],
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '<a href="https://github.com/example" class="link link-hover inline-flex items-center" target="_blank" rel="noopener" aria-label="GitHub">' in body
    assert 'https://cdn.simpleicons.org/github' in body


@pytest.mark.django_db
def test_home_활동_섹션은_첨부파일이_있으면_클립_아이콘과_개수를_보여준다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client

    from apps.profile.models import Activity, ActivityAttachment

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='첨부파일 렌더링 테스트', start_year=2026, order=100)
    ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('cert.pdf', b'dummy-bytes'), label='수료증',
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'paper-clip.svg' in body
    assert '>1</span>' in body
    assert '📄 수료증' in body


@pytest.mark.django_db
def test_home_활동_섹션의_첨부파일_드롭다운은_wrapper에서_esc키로_닫힌다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client

    from apps.profile.models import Activity, ActivityAttachment

    settings.MEDIA_ROOT = tmp_path
    activity = Activity.objects.create(name='ESC 테스트 활동', start_year=2026, order=100)
    ActivityAttachment.objects.create(
        activity=activity, file=SimpleUploadedFile('cert.pdf', b'dummy-bytes'),
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    # 드롭다운 트리거 버튼이 아니라 wrapper div에 @keydown.escape가 있어야, 메뉴 항목에
    # 포커스가 가 있을 때도 Escape로 닫힌다(버튼에만 있으면 포커스가 벗어나면 무반응).
    assert '<div class="dropdown" x-data="{ open: false }" :class="{ \'dropdown-open\': open }" @keydown.escape="open = false">' in body


@pytest.mark.django_db
def test_home_활동_섹션의_다년도_활동은_data_years_속성에_전체_연도가_담긴다() -> None:
    from django.test import Client

    from apps.profile.models import Activity

    Activity.objects.create(name='다년도 data-years 테스트', start_year=2022, end_year=2023, order=100)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'data-years="2022,2023"' in body


@pytest.mark.django_db
def test_home_활동_섹션은_링크와_첨부파일이_모두_없으면_아이콘_줄을_생략한다(settings, tmp_path) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client

    from apps.profile.models import Activity, ActivityAttachment

    settings.MEDIA_ROOT = tmp_path
    Activity.objects.create(name='아이콘_없음_테스트', start_year=2026, order=100)
    with_attachment = Activity.objects.create(name='아이콘_있음_테스트', start_year=2026, order=101)
    ActivityAttachment.objects.create(
        activity=with_attachment, file=SimpleUploadedFile('cert.pdf', b'dummy-bytes'),
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    # order=100인 '아이콘_없음_테스트'가 먼저, order=101인 '아이콘_있음_테스트'가 뒤에 렌더링된다.
    # 아이콘 줄 컨테이너(flex items-center gap-2 mt-2)가 전자 구간에는 없고 후자 구간에는
    # 있어야 "아예 렌더링 안 함"과 "우연히 아무 데도 없었음"을 구분해서 검증할 수 있다.
    no_icon_index = body.find('아이콘_없음_테스트')
    with_icon_index = body.find('아이콘_있음_테스트')
    no_icon_section = body[no_icon_index:with_icon_index]
    with_icon_section = body[with_icon_index:with_icon_index + 800]

    assert 'flex items-center gap-2 mt-2' not in no_icon_section
    assert 'flex items-center gap-2 mt-2' in with_icon_section


@pytest.mark.django_db
def test_home_자격증_카드는_고정_아이콘과_2열_grid를_사용한다() -> None:
    from django.test import Client

    from apps.profile.models import Certification

    Certification.objects.create(
        name='SQLD', issuer='한국데이터산업진흥원', acquired_date='2023-06-02', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'grid gap-3 sm:grid-cols-2' in body
    assert '<span class="text-2xl" aria-hidden="true">📜</span>' in body
