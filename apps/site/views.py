import json
from itertools import groupby

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
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
from apps.core.models import CRON_DAY_OF_WEEK_CHOICES, ScheduledJobConfig
from apps.core.services.rate_limit import check_rate_limit
from apps.engagement.models import Comment, Like
from apps.notifications.models import NoticeSource
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
    StudentSearchForm,
)
from apps.site.models import Tool
from apps.site.services.chatbot import ChatbotConfigError, get_chat_reply

# apps.core.models.CRON_DAY_OF_WEEK_CHOICES를 재사용해 요일 라벨을 lab 페이지 문구로 변환한다
_WEEKDAY_LABELS = dict(CRON_DAY_OF_WEEK_CHOICES)


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

    # 직장/학력/수상을 구분해 보여주기 위해 Skill과 동일한 방식으로 카테고리별로 그룹핑
    careers = sorted(Career.objects.all(), key=lambda c: (Career.Category.values.index(c.category), c.order))
    careers_by_category = {
        category: list(items) for category, items in groupby(careers, key=lambda c: c.category)
    }

    VisitorCounter.objects.get_or_create(pk=1)
    VisitorCounter.objects.filter(pk=1).update(count=F('count') + 1)
    total_stars = GithubProfileStats.objects.filter(pk=1).values_list('total_stars', flat=True).first() or 0

    return render(request, 'site/home.html', {
        'profile': profile,
        'bio_html': bio_html,
        'skills_by_category': skills_by_category,
        'pr_highlights': PullRequestHighlight.objects.all(),
        'featured_projects': Project.objects.order_by('order')[:3],
        'careers_by_category': careers_by_category,
        'activities': Activity.objects.all(),
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
    HX-Request 헤더가 있으면 사이드바+목록 프래그먼트만 반환한다.
    단, HX-History-Restore-Request(htmx 히스토리 캐시 미스로 인한 재요청)인 경우는
    htmx가 풀 페이지 응답을 기대하므로 예외로 취급한다."""
    category_slug = request.GET.get('category') or None
    context = {
        'posts': filter_published_posts_by_category_slug(category_slug),
        'sidebar_items': get_category_sidebar_items(),
        'selected_category_slug': category_slug,
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
    content_type = ContentType.objects.get_for_model(Post)
    comments = Comment.objects.filter(content_type=content_type, object_id=post.pk).select_related('author')
    like_count = Like.objects.filter(content_type=content_type, object_id=post.pk).count()
    is_liked = (
        request.user.is_authenticated
        and Like.objects.filter(content_type=content_type, object_id=post.pk, user=request.user).exists()
    )
    return render(
        request,
        'site/blog_detail.html',
        {
            'post': post,
            'content_html': content_html,
            'comments': comments,
            'like_count': like_count,
            'is_liked': is_liked,
        },
    )


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
    check_new_notices 잡의 ScheduledJobConfig를 조회해 수집 주기 문구를 함께 보여준다.
    """
    is_owner = request.user.is_authenticated and request.user.is_staff
    tools = Tool.objects.all()
    notice_sources = NoticeSource.objects.exclude(discord_webhook_url='').order_by('id')
    schedule_config = ScheduledJobConfig.objects.filter(job_id='check_new_notices').first()
    return render(request, 'site/lab_index.html', {
        'tools': tools,
        'is_owner': is_owner,
        'notice_sources': notice_sources,
        'notice_schedule_text': _format_notice_schedule_text(schedule_config),
        'discord_invite_url': settings.DISCORD_INVITE_URL,
    })


@owner_required
def lab_library(request: HttpRequest) -> HttpResponse:
    """스터디룸 예약 페이지 (소유자 전용)."""
    today = timezone.localdate().strftime('%Y%m%d')
    return render(request, 'site/lab_library.html', {'today': today})


@owner_required
def lab_library_rooms(request: HttpRequest) -> HttpResponse:
    """날짜별 스터디룸 가용 현황 조회 (htmx 부분 응답). 오류도 200으로 반환해 fragment가 그대로 swap되게 한다."""
    form = LibraryDateForm(request.GET)
    if not form.is_valid():
        return HttpResponse('날짜 형식이 올바르지 않습니다 (YYYYMMDD).', status=200)

    service = StudyRoomService()
    rooms = service.fetch_all_rooms(reserve_date=form.cleaned_data['reserve_date'])
    return render(
        request,
        'site/partials/library_rooms.html',
        {'rooms': rooms, 'reserve_date': form.cleaned_data['reserve_date']},
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
    except json.JSONDecodeError:
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

    try:
        reply = get_chat_reply(message, history)
    except ChatbotConfigError:
        return JsonResponse({'error': '챗봇 준비 중입니다. 잠시 후 다시 시도해주세요.'}, status=503)
    except SuhAiderClientError:
        return JsonResponse({'error': '일시적으로 응답할 수 없습니다. 잠시 후 다시 시도해주세요.'}, status=503)

    return JsonResponse({'reply': reply})


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
