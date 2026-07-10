from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.services.category import (
    filter_published_posts_by_category_slug,
    get_category_sidebar_items,
)
from apps.blog.services.markdown_renderer import render_markdown
from apps.engagement.models import Comment, Like
from apps.projects.models import Project
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


def home(request: HttpRequest) -> HttpResponse:
    """포트폴리오 랜딩 페이지."""
    return render(request, 'site/home.html')


def projects(request: HttpRequest) -> HttpResponse:
    """프로젝트 목록 페이지. 카테고리별로 그룹화해 보여준다."""
    project_list = Project.objects.all()
    return render(request, 'site/projects.html', {'projects': project_list})


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


def lab_index(request: HttpRequest) -> HttpResponse:
    """Lab 유틸 목록. 소유자 전용 도구는 소유자에게만 링크를 노출한다."""
    is_owner = request.user.is_authenticated and request.user.is_staff
    tools = Tool.objects.all()
    return render(request, 'site/lab_index.html', {'tools': tools, 'is_owner': is_owner})


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
