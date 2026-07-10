import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_페이지_200_응답() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))

    assert response.status_code == 200
    assert '백지훈' in response.content.decode()


@pytest.mark.django_db
def test_home_은_최근_활동_5건만_context에_담는다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.activity.models import GithubActivity

    for i in range(7):
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

    assert len(response.context['recent_activities']) == 5
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
def test_home_은_컨트리뷰션_데이터를_주단위로_묶어_context에_담는다() -> None:
    from datetime import date, timedelta

    from django.test import Client

    from apps.activity.models import GithubContributionDay

    # 상대 날짜 사용: home()이 date.today() 기준 371일 윈도우로 필터링하므로,
    # 하드코딩된 절대 날짜는 시간이 지나면 윈도우 밖으로 밀려나 테스트가 깨진다.
    start = date.today() - timedelta(days=30)
    for i in range(9):
        GithubContributionDay.objects.create(date=start + timedelta(days=i), contribution_count=i)

    client = Client()
    response = client.get(reverse('site:home'))
    weeks = response.context['contribution_weeks']

    assert len(weeks) == 2
    assert len(weeks[0]) == 7
    assert len(weeks[1]) == 2


@pytest.mark.django_db
def test_home_은_1년보다_오래된_컨트리뷰션은_제외한다() -> None:
    from datetime import date, timedelta

    from django.test import Client

    from apps.activity.models import GithubContributionDay

    old_date = date.today() - timedelta(days=400)
    recent_date = date.today() - timedelta(days=10)
    GithubContributionDay.objects.create(date=old_date, contribution_count=1)
    GithubContributionDay.objects.create(date=recent_date, contribution_count=2)

    client = Client()
    response = client.get(reverse('site:home'))
    all_days = [day for week in response.context['contribution_weeks'] for day in week]
    all_dates = [day.date for day in all_days]

    assert old_date not in all_dates
    assert recent_date in all_dates


@pytest.mark.django_db
def test_projects_페이지는_카테고리별_프로젝트를_보여준다() -> None:
    from django.test import Client

    from apps.projects.models import Project, ProjectCategory, ProjectStatus

    Project.objects.create(
        category=ProjectCategory.SIDE,
        title='개인 홈서버',
        description='Django 홈서버',
        status=ProjectStatus.IN_PROGRESS,
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
def test_home_템플릿은_활동_아이콘과_제목을_보여준다() -> None:
    from django.test import Client
    from django.utils import timezone

    from apps.activity.models import GithubActivity

    GithubActivity.objects.create(
        event_id='evt-1', event_type='PushEvent', repo_name='chuseok22/test-repo',
        title='chuseok22/test-repo', meta='커밋 메시지', occurred_at=timezone.now(),
    )

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '📝' in body
    assert 'chuseok22/test-repo' in body
    assert '커밋 메시지' in body


@pytest.mark.django_db
def test_home_템플릿은_활동이_없으면_안내_문구를_보여준다() -> None:
    from django.test import Client

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '아직 기록된 활동이 없습니다.' in body


@pytest.mark.django_db
def test_home_템플릿은_총_star_수를_보여준다() -> None:
    from django.test import Client

    from apps.activity.models import GithubProfileStats

    GithubProfileStats.objects.create(pk=1, total_stars=8)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert '⭐ 8' in body


@pytest.mark.django_db
def test_home_템플릿은_컨트리뷰션_데이터가_있으면_그리드를_렌더링한다() -> None:
    from datetime import date, timedelta

    from django.test import Client

    from apps.activity.models import GithubContributionDay

    # 상대 날짜 사용: home()이 date.today() 기준 371일 윈도우로 필터링하므로,
    # 하드코딩된 절대 날짜는 시간이 지나면 윈도우 밖으로 밀려나 테스트가 깨진다.
    # contribution_count=7 -> Task 6의 contribution_level_class 경계값(7~9)에서 'bg-success/80' 반환
    GithubContributionDay.objects.create(date=date.today() - timedelta(days=30), contribution_count=7)

    client = Client()
    response = client.get(reverse('site:home'))
    body = response.content.decode()

    assert 'bg-success/80' in body
