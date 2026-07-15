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
def test_home_은_최근_활동_10건까지_context에_담는다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.activity.models import GithubActivity

    for i in range(12):
        GithubActivity.objects.create(
            event_id=f'evt-{i}',
            event_type='PushEvent',
            repo_name='chuseok22/test-repo',
            title='커밋',
            meta=f'메시지 {i}',
            occurred_at=timezone.now() - timezone.timedelta(hours=i),
        )

    client = Client()
    response = client.get(reverse('site:home'))

    assert len(response.context['recent_activities']) == 10
    assert response.context['recent_activities'][0].event_id == 'evt-0'


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

    client = Client()
    first = client.get(reverse('site:home'))
    second = client.get(reverse('site:home'))

    assert first.context['visitor_count'] == 1
    assert second.context['visitor_count'] == 2


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
def test_home_은_대표_프로젝트를_order_기준_상위_3개만_전달한다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    category = ProjectCategory.objects.get(name='사이드 프로젝트')
    status = ProjectStatus.objects.get(name='진행중')
    for i in range(5):
        Project.objects.create(
            category=category, title=f'프로젝트 {i}', description='설명', status=status, order=i,
        )

    client = Client()
    response = client.get(reverse('site:home'))
    featured = list(response.context['featured_projects'])

    assert len(featured) == 3
    assert [p.title for p in featured] == ['프로젝트 0', '프로젝트 1', '프로젝트 2']


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

    assert re.search(r'<p class="opacity-50 text-xs mt-1 flex items-center gap-1">.*?5</p>', response.content.decode(), re.DOTALL)


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

    assert re.search(r'<p class="opacity-50 text-xs mt-1 flex items-center gap-1">.*?7</p>', response.content.decode(), re.DOTALL)


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
def test_home_템플릿은_수상_데이터가_없으면_수상_헤더를_보여주지_않는다() -> None:
    from django.test import Client

    from apps.profile.models import Career

    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=0,
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '수상' not in body


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

    assert 'M12 .297c-6.63 0-12 5.373-12 12' in body


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

    assert body.count('class="section-box') == 2


@pytest.mark.django_db
def test_home_템플릿은_프로필과_기술스택_섹션도_박스로_보여준다() -> None:
    from django.test import Client

    from apps.profile.models import Profile, Skill

    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert body.count('class="section-box') == 4


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
