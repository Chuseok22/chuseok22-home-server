import json
import logging
from itertools import groupby

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import F
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.activity.models import GithubProfileStats
from apps.ai.services.suh_aider_client import SuhAiderClientError
from apps.blog.models import Post
from apps.blog.services.category import (
    filter_published_posts_by_category_slug,
    get_category_sidebar_items,
)
from apps.blog.services.markdown_renderer import render_markdown
from apps.blog.services.media_storage import save_uploaded_media
from apps.blog.services.post_editor import update_post_content
from apps.certifications.models import CertificationDefinition
from apps.certifications.services.calendar import (
    build_month_calendar,
    get_tracked_certifications,
    get_upcoming_schedules,
)
from apps.core.models import CRON_DAY_OF_WEEK_CHOICES, ScheduledJobConfig
from apps.core.services.rate_limit import check_rate_limit
from apps.engagement.models import Comment, Like
from apps.notifications.models import NoticeSource
from apps.places.models import Place, PlaceSuggestion, PlaceTag
from apps.profile.models import (
    Activity,
    Career,
    Certification,
    Profile,
    PullRequestHighlight,
    Skill,
    VisitorCounter,
)
from apps.projects.models import Project
from apps.projects.services.category import (
    filter_projects_by_category_id,
    get_project_category_sidebar_items,
)
from apps.sejong.library.models import ReservationAttendee, ReservationHistory
from apps.sejong.library.services.my_reservations import MyReservationsService
from apps.sejong.library.services.slounge import SloungeService
from apps.sejong.library.services.study_room import StudyRoomService
from apps.sejong.library.services.study_room_reservation import (
    AttendeeParams,
    ReservationParams,
    StudyRoomReservationService,
)
from apps.sejong.student.services.student_search import StudentSearchService
from apps.site.decorators import owner_required
from apps.site.forms import (
    LibraryDateForm,
    LibraryReserveForm,
    LibraryReserveSlotForm,
    PlaceSuggestionForm,
    PostEditForm,
    StudentSearchForm,
)
from apps.site.models import Tool
from apps.site.services.chatbot import ChatbotConfigError, get_chat_reply
from apps.site.services.library_matrix import build_room_matrix

logger = logging.getLogger(__name__)

# apps.core.models.CRON_DAY_OF_WEEK_CHOICES를 재사용해 요일 라벨을 lab 페이지 문구로 변환한다
_WEEKDAY_LABELS = dict(CRON_DAY_OF_WEEK_CHOICES)

# NoticeSource.crawler_type별로 실제 수집을 구동하는 ScheduledJobConfig.job_id 매핑.
# github_trending만 check_new_notices가 아닌 별도 잡(send_github_trending_report)으로 운영되고,
# 나머지 crawler_type(sejong, sejong_do, linkareer, dacon, dreamspon)은 모두 check_new_notices가
# 기본으로 구동하므로 매핑에 없는 crawler_type은 _DEFAULT_NOTICE_JOB_ID로 처리한다.
_JOB_ID_BY_CRAWLER_TYPE = {'github_trending': 'send_github_trending_report'}
_DEFAULT_NOTICE_JOB_ID = 'check_new_notices'

_BLOG_SORT_OPTIONS = {
    # published_at은 null 허용 필드라 공개 글이라도 값이 없을 수 있다.
    # NULL을 기본(DESC=NULLS FIRST) 규칙대로 두면 날짜 없는 글이 "최신"으로 보여 nulls_last로 맨 뒤로 보낸다.
    'latest': F('published_at').desc(nulls_last=True),
    'views': '-views_count',
}
_DEFAULT_BLOG_SORT = 'latest'


def home(request: HttpRequest) -> HttpResponse:
    """포트폴리오 랜딩 페이지. 프로필 소개·기술스택·이력·PR/프로젝트 하이라이트와
    사이드바(최근 글)를 함께 보여준다."""
    profile = Profile.objects.first()
    bio_html = render_markdown(profile.bio) if profile and profile.bio else ''

    # Meta.ordering은 알파벳순(database → etc → frontend)이므로, 정의 순서(backend → frontend → database → ... → etc)로 정렬하기 위해 Python에서 재정렬
    skills = sorted(Skill.objects.all(), key=lambda s: (Skill.Category.values.index(s.category), s.order))
    skills_by_category = {
        category: list(items) for category, items in groupby(skills, key=lambda s: s.category)
    }

    # 수상(AWARD)은 이력이 아닌 별도 Awards & Honors 섹션에서 보여주므로 이력 그룹핑에서 제외한다
    careers = sorted(
        Career.objects.exclude(category=Career.Category.AWARD),
        key=lambda c: (Career.Category.values.index(c.category), c.order),
    )
    careers_by_category = {
        category: list(items) for category, items in groupby(careers, key=lambda c: c.category)
    }
    awards = Career.objects.filter(category=Career.Category.AWARD).order_by('order')

    VisitorCounter.objects.get_or_create(pk=1)
    VisitorCounter.objects.filter(pk=1).update(count=F('count') + 1)
    total_stars = GithubProfileStats.objects.filter(pk=1).values_list('total_stars', flat=True).first() or 0

    activities = Activity.objects.prefetch_related('attachments')
    activity_years = sorted({year for activity in activities for year in activity.years}, reverse=True)

    return render(request, 'site/home.html', {
        'profile': profile,
        'bio_html': bio_html,
        'skills_by_category': skills_by_category,
        'pr_highlights': PullRequestHighlight.objects.all(),
        'featured_projects': Project.objects.filter(is_featured=True).order_by('order'),
        'careers_by_category': careers_by_category,
        'awards': awards,
        'activities': activities,
        'activity_years': activity_years,
        'certifications': Certification.objects.all(),
        'recent_posts': Post.objects.filter(is_published=True).order_by('-published_at')[:3],
        'total_stars': total_stars,
    })


def projects(request: HttpRequest) -> HttpResponse:
    """프로젝트 목록 페이지. ?category=<id>로 카테고리 필터링,
    HX-Request 헤더가 있으면(히스토리 복원 요청 제외) 사이드바+목록 프래그먼트만 반환한다."""
    raw_category_id = request.GET.get('category')
    # str.isdigit()은 '²' 같은 비-십진 유니코드 숫자에도 True를 반환해 int() 호출이
    # ValueError로 500 에러를 낼 수 있다. isdecimal()만 순수 10진 문자열에 True를 반환한다.
    category_id = int(raw_category_id) if raw_category_id and raw_category_id.isdecimal() else None
    context = {
        'projects': filter_projects_by_category_id(category_id),
        'sidebar_items': get_project_category_sidebar_items(),
        'selected_category_id': category_id,
        'total_project_count': Project.objects.count(),
    }
    is_htmx_fragment_request = (
        request.headers.get('HX-Request') and not request.headers.get('HX-History-Restore-Request')
    )
    template_name = 'site/partials/projects_content.html' if is_htmx_fragment_request else 'site/projects.html'
    return render(request, template_name, context)


def blog_list(request: HttpRequest) -> HttpResponse:
    """공개된 블로그 포스트 목록. ?category=<slug>로 카테고리 필터링,
    ?sort=latest(기본값)|views로 정렬,
    HX-Request 헤더가 있으면 사이드바+목록 프래그먼트만 반환한다.
    단, HX-History-Restore-Request(htmx 히스토리 캐시 미스로 인한 재요청)인 경우는
    htmx가 풀 페이지 응답을 기대하므로 예외로 취급한다."""
    category_slug = request.GET.get('category') or None
    sort = request.GET.get('sort')
    if sort not in _BLOG_SORT_OPTIONS:
        sort = _DEFAULT_BLOG_SORT

    posts = filter_published_posts_by_category_slug(category_slug).order_by(_BLOG_SORT_OPTIONS[sort])
    context = {
        'posts': posts,
        'sidebar_items': get_category_sidebar_items(),
        'selected_category_slug': category_slug,
        'current_sort': sort,
        'total_post_count': Post.objects.filter(is_published=True).count(),
    }
    is_htmx_fragment_request = (
        request.headers.get('HX-Request') and not request.headers.get('HX-History-Restore-Request')
    )
    template_name = 'site/partials/blog_content.html' if is_htmx_fragment_request else 'site/blog_list.html'
    return render(request, template_name, context)


def blog_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """블로그 포스트 상세. 비공개 포스트는 404."""
    post = get_object_or_404(Post, slug=slug, is_published=True)
    Post.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
    post.views_count += 1
    content_html = render_markdown(post.content)
    has_mermaid = 'class="mermaid"' in content_html
    content_type = ContentType.objects.get_for_model(Post)
    comments = Comment.objects.filter(content_type=content_type, object_id=post.pk).select_related('author')
    like_count = Like.objects.filter(content_type=content_type, object_id=post.pk).count()
    is_liked = (
        request.user.is_authenticated
        and Like.objects.filter(content_type=content_type, object_id=post.pk, user=request.user).exists()
    )
    is_owner = request.user.is_authenticated and request.user.is_staff
    return render(
        request,
        'site/blog_detail.html',
        {
            'post': post,
            'content_html': content_html,
            'has_mermaid': has_mermaid,
            'comments': comments,
            'like_count': like_count,
            'is_liked': is_liked,
            'is_owner': is_owner,
        },
    )


@owner_required
@require_POST
def blog_post_edit(request: HttpRequest, slug: str) -> JsonResponse:
    """발행된 블로그 글의 제목·요약·본문을 인라인으로 수정한다 (소유자 전용).
    성공/실패 모두 JSON으로 응답하며, 프런트엔드는 성공 시 페이지를 새로고침해
    목차·코드블록 복사버튼·mermaid까지 서버 렌더링 결과로 갱신한다."""
    post = get_object_or_404(Post, slug=slug, is_published=True)
    form = PostEditForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)

    update_post_content(
        post,
        title=form.cleaned_data['title'],
        summary=form.cleaned_data['summary'],
        content=form.cleaned_data['content'],
    )
    return JsonResponse({'success': True})


@owner_required
@require_POST
def blog_post_upload_image(request: HttpRequest) -> JsonResponse:
    """블로그 글 인라인 수정 중 이미지 업로드 (소유자 전용). 특정 글에 종속되지 않는 공용
    엔드포인트이며, Admin의 PostAdmin.upload_media_view와 동일하게 media_storage 서비스를 재사용한다."""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error_message': '업로드할 파일이 없습니다.'}, status=400)

    result = save_uploaded_media(request.FILES['file'])
    if not result.success:
        return JsonResponse({'success': False, 'error_message': result.error_message}, status=400)

    return JsonResponse({'success': True, 'url': result.url, 'markdown': result.markdown})


_PLACES_PER_PAGE = 30


def _place_filter_query(tag_ids: list[int], category: str | None, page: int | None = None) -> str:
    """태그·카테고리·페이지 필터 링크의 querystring을 만든다.
    tags는 항상 먼저, category, page 순으로 넣어 링크 순서를 예측 가능하게 고정한다."""
    query = QueryDict(mutable=True)
    if tag_ids:
        query.setlist('tags', tag_ids)
    if category:
        query['category'] = category
    if page and page > 1:
        query['page'] = page
    return query.urlencode()


def places(request: HttpRequest) -> HttpResponse:
    """장소 목록 페이지. ?tags=<id>(다중 가능)&category=<value>&page=<n>으로 필터링,
    HX-Request 헤더가 있으면(히스토리 복원 요청 제외) 목록 프래그먼트만 반환한다.
    카드 목록과 지도 마커 모두 현재 페이지 항목만 표시한다(전체 장소가 1,000건이 넘어
    한 페이지에 전부 렌더링하면 무거워지므로)."""
    tag_ids = [int(value) for value in request.GET.getlist('tags') if value.isdecimal()]
    category = request.GET.get('category') or None

    queryset = Place.objects.prefetch_related('tags')
    if tag_ids:
        queryset = queryset.filter(tags__id__in=tag_ids).distinct()
    if category:
        queryset = queryset.filter(category=category)

    paginator = Paginator(queryset, _PLACES_PER_PAGE)
    page_number = request.GET.get('page', '1')
    page_obj = paginator.get_page(page_number if page_number.isdecimal() else 1)

    tag_filters = [
        {
            'tag': tag,
            'is_selected': tag.id in tag_ids,
            'query': _place_filter_query(
                [t for t in tag_ids if t != tag.id] if tag.id in tag_ids else [*tag_ids, tag.id],
                category,
            ),
        }
        for tag in PlaceTag.objects.all()
    ]
    category_filters = [
        {
            'value': value,
            'label': label,
            'is_selected': category == value,
            'query': _place_filter_query(tag_ids, None if category == value else value),
        }
        for value, label in Place.Category.choices
    ]

    context = {
        'places': page_obj,
        'page_obj': page_obj,
        'prev_query': _place_filter_query(tag_ids, category, page_obj.previous_page_number()) if page_obj.has_previous() else '',
        'next_query': _place_filter_query(tag_ids, category, page_obj.next_page_number()) if page_obj.has_next() else '',
        'tag_filters': tag_filters,
        'category_filters': category_filters,
        'has_any_filter': bool(tag_ids or category),
        'kakao_js_api_key': settings.KAKAO_JS_API_KEY,
    }
    is_htmx_fragment_request = (
        request.headers.get('HX-Request') and not request.headers.get('HX-History-Restore-Request')
    )
    template_name = 'site/partials/places_content.html' if is_htmx_fragment_request else 'site/places.html'
    return render(request, template_name, context)


def place_suggest(request: HttpRequest) -> HttpResponse:
    """방문자 장소 제보 폼. GET은 로그인 여부와 관계없이 200을 반환하고(비로그인은
    템플릿에서 로그인 안내로 대체), 제출(POST)은 로그인 사용자만 처리해 검토 대기
    큐(PlaceSuggestion)에 저장한다. @login_required로 감싸면 비로그인 GET이
    로그인 페이지로 리다이렉트되어 "폼 대신 로그인 안내를 보여준다"는 요구사항과
    충돌하므로, 인증 분기를 뷰 안에서 직접 처리한다. 제출은 챗봇 엔드포인트와 동일한
    check_rate_limit 유틸로 IP당 분당 5회로 제한한다.

    저장 성공 후에는 PRG(Post/Redirect/Get) 패턴으로 리다이렉트한다 — 저장 후 같은
    POST 응답을 그대로 렌더링하면 새로고침 시 동일한 PlaceSuggestion이 중복
    생성되므로, 성공 표시는 리다이렉트된 GET의 ?submitted=1 쿼리 파라미터로 전달한다."""
    if request.method == 'POST' and request.user.is_authenticated:
        if not check_rate_limit(request, key='place-suggest', limit=5, window_seconds=60):
            form = PlaceSuggestionForm(request.POST)
            return render(
                request, 'site/place_suggest.html',
                {'form': form, 'submitted': False, 'rate_limited': True},
                status=429,
            )

        form = PlaceSuggestionForm(request.POST)
        if form.is_valid():
            PlaceSuggestion.objects.create(
                restaurant_name=form.cleaned_data['restaurant_name'],
                kakao_place_url=form.cleaned_data['kakao_place_url'],
                message=form.cleaned_data['message'],
                submitted_by=request.user,
            )
            return redirect(f"{reverse('site:place-suggest')}?submitted=1")
    else:
        form = PlaceSuggestionForm()

    submitted = request.GET.get('submitted') == '1'
    return render(request, 'site/place_suggest.html', {'form': form, 'submitted': submitted})


def place_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """장소 상세 페이지. 댓글·좋아요를 붙이기 위한 페이지."""
    place = get_object_or_404(Place.objects.prefetch_related('tags'), pk=pk)
    content_type = ContentType.objects.get_for_model(Place)
    comments = Comment.objects.filter(content_type=content_type, object_id=place.pk).select_related('author')
    like_count = Like.objects.filter(content_type=content_type, object_id=place.pk).count()
    is_liked = (
        request.user.is_authenticated
        and Like.objects.filter(content_type=content_type, object_id=place.pk, user=request.user).exists()
    )
    return render(
        request,
        'site/place_detail.html',
        {
            'place': place,
            'comments': comments,
            'like_count': like_count,
            'is_liked': is_liked,
        },
    )


# calendar.monthdatescalendar()는 연도가 datetime.MINYEAR/MAXYEAR 부근을 벗어나면(특히 그리드가
# 걸치는 인접 연도까지 넘어가면) ValueError를 던진다 — 공개 페이지에서 ?year= 쿼리파라미터로
# 임의 값이 들어올 수 있으므로 안전한 범위로 제한한다.
_MIN_CALENDAR_YEAR = 1900
_MAX_CALENDAR_YEAR = 2100


def _parse_int(value: str | None, default: int) -> int:
    # int()는 Python 3.11+부터 4300자리를 넘는 십진수 문자열 변환을 ValueError로 거부한다 —
    # isdecimal()만으로는 자릿수를 걸러내지 못하므로, year/month 용도로 충분한 자릿수로
    # 미리 제한해 변환 자체가 항상 안전하도록 만든다.
    if not value or not value.isdecimal() or len(value) > 9:
        return default
    return int(value)


def certifications(request: HttpRequest) -> HttpResponse:
    """자격증 시험일정 캘린더 페이지. ?year=&month=로 월 이동, ?category=로 카테고리 필터링,
    HX-Request 헤더가 있으면(히스토리 복원 요청 제외) 프래그먼트만 반환한다."""
    today = timezone.localdate()
    year = _parse_int(request.GET.get('year'), today.year)
    month = _parse_int(request.GET.get('month'), today.month)
    if not (1 <= month <= 12) or not (_MIN_CALENDAR_YEAR <= year <= _MAX_CALENDAR_YEAR):
        year, month = today.year, today.month

    category = request.GET.get('category') or None
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    upcoming_schedules = get_upcoming_schedules(today, category)
    for schedule in upcoming_schedules:
        # DB에 저장된 필드가 아니라 템플릿에 D-day를 보여주기 위한 뷰 레벨 계산값이다.
        schedule.days_until_deadline = (schedule.registration_end - today).days

    context = {
        'weeks': build_month_calendar(year, month, category),
        'year': year,
        'month': month,
        'today': today,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'upcoming_schedules': upcoming_schedules,
        'tracked_certifications': get_tracked_certifications(category),
        'category_choices': CertificationDefinition.Category.choices,
        'selected_category': category,
    }
    is_htmx_fragment_request = (
        request.headers.get('HX-Request') and not request.headers.get('HX-History-Restore-Request')
    )
    template_name = (
        'site/partials/certifications_content.html' if is_htmx_fragment_request else 'site/certifications.html'
    )
    return render(request, template_name, context)


def _format_notice_schedule_text(config: ScheduledJobConfig | None) -> str:
    """ScheduledJobConfig 설정값을 lab 페이지에 표시할 한국어 문구로 변환한다.

    공개 페이지(비로그인 접근 가능)에서 호출되므로, 예상 밖의 설정값(cron_day_of_week 오타,
    interval_hours 미설정, fixed_hours에 숫자가 아닌 토큰 등)이 있어도 예외를 던지지 않고
    안전한 기본 문구로 대체한다. is_enabled가 False면 실제로는 수집이 멈춘 상태이므로
    운영 중인 것처럼 보이지 않도록 별도 문구를 반환한다.
    """
    if config is None:
        return '자동 수집 일정 미설정'
    if not config.is_enabled:
        return '자동 수집 일시 중단'

    if config.cron_day_of_week == '*':
        day_prefix = '매일'
    else:
        day_labels = [
            _WEEKDAY_LABELS.get(token, token) for token in config.cron_day_of_week.split(',')
        ]
        day_prefix = '매주 ' + ', '.join(day_labels)

    if config.schedule_mode == 'interval':
        if config.interval_hours is None or config.interval_hours == 24:
            return f'{day_prefix} 자동 수집'
        return f'{day_prefix} {config.interval_hours}시간마다 자동 수집'

    # clean()을 거치지 않는 경로(관리 커맨드, 데이터 마이그레이션 등)로 저장된 값이 섞여
    # 있어도 int() 변환에서 예외가 나지 않도록 숫자 토큰만 사용한다. str.isdigit()은 '²' 같은
    # 비-십진 유니코드 숫자에도 True를 반환해 int() 호출이 ValueError를 낼 수 있으므로(이미
    # apps/site/views.py의 projects 뷰에서 겪은 문제) isdecimal()만 순수 10진 문자열에 True를
    # 반환하는 이 메서드를 사용한다.
    hours = [h for h in config.fixed_hours.split(',') if h.strip().isdecimal()]
    if not hours:
        return f'{day_prefix} 자동 수집'
    times = ', '.join(f'{int(h):02d}:{config.fixed_minute:02d}' for h in hours)
    return f'{day_prefix} {times} 자동 수집'


def lab_index(request: HttpRequest) -> HttpResponse:
    """Lab 유틸 목록. 소유자 전용 도구는 소유자에게만 링크를 노출한다.

    자동 알리미 섹션은 discord_webhook_url이 설정된(즉 한 번이라도 Discord에 연동된)
    NoticeSource만 노출한다(비활성 포함). 웹훅이 없는 소스는 check_new_notices가 발송
    자체를 건너뛰므로, 애초에 노출하지 않아야 "운영 중"처럼 보이는 오해를 막을 수 있다.
    소스마다 실제로 수집을 구동하는 ScheduledJobConfig가 다를 수 있으므로(예: github_trending은
    check_new_notices가 아니라 send_github_trending_report), 소스별 crawler_type에 맞는
    ScheduledJobConfig를 조회해 수집 주기 문구를 카드마다 개별적으로 보여준다.
    """
    is_owner = request.user.is_authenticated and request.user.is_staff
    tools = Tool.objects.all()
    notice_sources = list(NoticeSource.objects.exclude(discord_webhook_url='').order_by('id'))
    job_ids = {_DEFAULT_NOTICE_JOB_ID, *_JOB_ID_BY_CRAWLER_TYPE.values()}
    configs_by_job_id = {
        config.job_id: config
        for config in ScheduledJobConfig.objects.filter(job_id__in=job_ids)
    }
    for source in notice_sources:
        job_id = _JOB_ID_BY_CRAWLER_TYPE.get(source.crawler_type, _DEFAULT_NOTICE_JOB_ID)
        source.schedule_text = _format_notice_schedule_text(configs_by_job_id.get(job_id))
    return render(request, 'site/lab_index.html', {
        'tools': tools,
        'is_owner': is_owner,
        'notice_sources': notice_sources,
        'discord_invite_url': settings.DISCORD_INVITE_URL,
    })


@owner_required
def lab_library(request: HttpRequest) -> HttpResponse:
    """스터디룸 예약 페이지 (소유자 전용)."""
    today = timezone.localdate().strftime('%Y%m%d')
    return render(request, 'site/lab_library.html', {'today': today})


@owner_required
def lab_library_rooms(request: HttpRequest) -> HttpResponse:
    """날짜별 스터디룸/S-Lounge 가용 현황 조회 (htmx 부분 응답). 오류도 200으로 반환해 fragment가 그대로 swap되게 한다."""
    form = LibraryDateForm(request.GET)
    if not form.is_valid():
        return HttpResponse('날짜 형식이 올바르지 않습니다 (YYYYMMDD).', status=200)

    room_type = form.cleaned_data['room_type']
    if room_type == 's_lounge':
        rooms = SloungeService().fetch_all_lounges(reserve_date=form.cleaned_data['reserve_date'])
    else:
        rooms = StudyRoomService().fetch_all_rooms(reserve_date=form.cleaned_data['reserve_date'])

    return render(
        request,
        'site/partials/library_rooms.html',
        {
            'matrix': build_room_matrix(rooms),
            'reserve_date': form.cleaned_data['reserve_date'],
            'room_type': room_type,
        },
    )


@owner_required
def lab_library_reserve_form(request: HttpRequest) -> HttpResponse:
    """가용 현황 그리드에서 슬롯을 선택했을 때 예약 입력 폼을 반환한다 (htmx 부분 응답)."""
    slot_form = LibraryReserveSlotForm(request.GET)
    if not slot_form.is_valid():
        return HttpResponse('슬롯 정보가 올바르지 않습니다.', status=200)

    return render(request, 'site/partials/library_reserve_form.html', {'slot': slot_form.cleaned_data})


@owner_required
def lab_library_reserve(request: HttpRequest) -> HttpResponse:
    """스터디룸 예약 요청 처리 (htmx 부분 응답). 검증 실패·서비스 실패 모두 200으로 반환한다."""
    form = LibraryReserveForm(request.POST)
    if not form.is_valid():
        return render(request, 'site/partials/library_result.html', {'errors': form.errors}, status=200)

    data = form.cleaned_data
    attendees = tuple(
        AttendeeParams(student_id=a['student_id'], name=a['name']) for a in data['attendees_raw']
    )
    params = ReservationParams(
        room_no=data['room_no'],
        room_gb=data['room_gb'],
        seat_cnt=data['seat_cnt'],
        sroom_title=data['sroom_title'],
        room_name=data['room_name'],
        seq=data['seq'],
        reserve_date=data['reserve_date'],
        start_time=data['start_time'],
        use_time=int(data['use_time']),
        attendees=attendees,
    )

    service = StudyRoomReservationService()
    result = service.reserve(params)

    ReservationHistory.objects.create(
        room_no=result.room_no,
        room_name=result.room_name,
        reserve_date=data['reserve_date'],
        start_time=data['start_time'],
        use_time=int(data['use_time']),
        attendees_json=data['attendees_raw'],
        result_code=result.result_code,
        result_message=result.result_message,
    )
    if result.success:
        for attendee in attendees:
            ReservationAttendee.objects.get_or_create(
                student_id=attendee.student_id, defaults={'name': attendee.name},
            )

    return render(request, 'site/partials/library_result.html', {'result': result})


@owner_required
def lab_library_my_reservations(request: HttpRequest) -> HttpResponse:
    """mySeat.php 기반 내 예약 현황 페이지 (소유자 전용, 조회 전용)."""
    try:
        items = MyReservationsService().fetch_all()
    except ValueError as e:
        logger.error('내 예약 현황 서비스 설정 오류 (자격증명 누락): %s', e)
        return render(
            request,
            'site/lab_library_my_reservations.html',
            {'items': None, 'fetch_failed': True},
            status=503,
        )

    if items is None:
        return render(
            request,
            'site/lab_library_my_reservations.html',
            {'items': None, 'fetch_failed': True},
            status=503,
        )
    return render(request, 'site/lab_library_my_reservations.html', {'items': items})


@owner_required
def lab_student(request: HttpRequest) -> HttpResponse:
    """학생 조회 페이지 (소유자 전용)."""
    return render(request, 'site/lab_student.html')


@owner_required
def lab_student_search(request: HttpRequest) -> HttpResponse:
    """학생 조회 요청 처리 (htmx 부분 응답). 검증 실패·외부 서비스 오류 모두 200으로 반환한다."""
    form = StudentSearchForm(request.GET)
    if not form.is_valid():
        return HttpResponse('이름 또는 학번 중 하나만 입력하세요.', status=200)

    service = StudentSearchService()
    data = form.cleaned_data
    if data['name']:
        results = service.search_by_name(data['name'])
    else:
        results = service.search_by_student_no(data['student_no'])

    if results is None:
        return HttpResponse('세종대 Classic 서비스에 연결할 수 없습니다.', status=200)

    return render(request, 'site/partials/student_results.html', {'results': results})


_CHAT_MAX_MESSAGE_LENGTH = 2000
_CHAT_MAX_HISTORY_ITEMS = 20
_CHAT_ALLOWED_HISTORY_ROLES = {'user', 'assistant'}


@require_POST
def chat(request: HttpRequest) -> JsonResponse:
    """전역 챗봇 위젯의 메시지 전송을 처리한다. 로그인 불필요, IP당 분당 5회로 제한한다."""
    if not check_rate_limit(request, key='chat', limit=5, window_seconds=60):
        return JsonResponse({'error': '잠시 후 다시 시도해주세요.'}, status=429)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    message = payload.get('message')
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({'error': '메시지를 입력해주세요.'}, status=400)
    message = message.strip()
    if len(message) > _CHAT_MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': '메시지가 너무 깁니다.'}, status=400)

    history = payload.get('history') if payload.get('history') is not None else []
    if not _is_valid_chat_history(history):
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
    # role/content 외 임의의 추가 키(예: images)가 그대로 업스트림 SUH-AIder API로 전달되지
    # 않도록, 검증을 통과한 항목이라도 허용된 두 필드만 남기고 재구성한다.
    history = [{'role': item['role'], 'content': item['content']} for item in history]

    try:
        result = get_chat_reply(message, history)
    except ChatbotConfigError:
        return JsonResponse({'error': '챗봇 준비 중입니다. 잠시 후 다시 시도해주세요.'}, status=503)
    except SuhAiderClientError:
        return JsonResponse({'error': '일시적으로 응답할 수 없습니다. 잠시 후 다시 시도해주세요.'}, status=503)

    return JsonResponse({
        'reply': result.text,
        'links': [{'label': link.label, 'url': link.url} for link in result.links],
    })


def _is_valid_chat_history(history: object) -> bool:
    # 클라이언트가 role: 'system'을 주입해 시스템 프롬프트를 덮어쓰려는 시도를 막기 위해
    # user/assistant만 허용한다. 항목 수·길이 상한은 Django 기본 DATA_UPLOAD_MAX_MEMORY_SIZE만으로는
    # 항목당 길이가 사실상 무제한이라(요청 전체 크기만 제한됨) 별도로 강제한다.
    if not isinstance(history, list) or len(history) > _CHAT_MAX_HISTORY_ITEMS:
        return False
    for item in history:
        if not isinstance(item, dict):
            return False
        if item.get('role') not in _CHAT_ALLOWED_HISTORY_ROLES:
            return False
        content = item.get('content')
        if not isinstance(content, str) or len(content) > _CHAT_MAX_MESSAGE_LENGTH:
            return False
    return True
