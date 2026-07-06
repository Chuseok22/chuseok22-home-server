from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.blog.models import Post
from apps.core.scheduler import JOB_DEFINITIONS, get_or_seed_job_config, get_scheduler
from apps.core.services.scheduler_service import update_job_schedule
from apps.dashboard.decorators import dashboard_required
from apps.dashboard.forms import PostForm, ProjectForm, ScheduledJobConfigForm
from apps.projects.models import Project


@dashboard_required
def home(request: HttpRequest) -> HttpResponse:
    """대시보드 홈. 하위 관리 화면으로 이동하는 진입점."""
    return render(request, 'dashboard/home.html')


# --- Project CRUD ---

@dashboard_required
def project_list(request: HttpRequest) -> HttpResponse:
    """프로젝트 목록 페이지."""
    return render(request, 'dashboard/projects/list.html', {'projects': Project.objects.all()})


@dashboard_required
def project_table_body(request: HttpRequest) -> HttpResponse:
    """프로젝트 목록 테이블 본문 (htmx 부분 응답 — 취소·목록 복귀 시 사용)."""
    return render(request, 'dashboard/projects/_table_body.html', {'projects': Project.objects.all()})


@dashboard_required
def project_form(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    """프로젝트 생성/수정 폼 (htmx 부분 응답). GET은 폼을, POST는 검증 후 저장 결과를 반환한다."""
    project = get_object_or_404(Project, pk=pk) if pk else None

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return render(request, 'dashboard/projects/_table_body.html', {'projects': Project.objects.all()})
        return render(request, 'dashboard/projects/_form.html', {'form': form, 'project': project}, status=200)

    form = ProjectForm(instance=project)
    return render(request, 'dashboard/projects/_form.html', {'form': form, 'project': project})


@dashboard_required
@require_POST
def project_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """프로젝트 삭제 (htmx 부분 응답)."""
    project = get_object_or_404(Project, pk=pk)
    project.delete()
    return render(request, 'dashboard/projects/_table_body.html', {'projects': Project.objects.all()})


# --- Post CRUD ---

@dashboard_required
def post_list(request: HttpRequest) -> HttpResponse:
    """블로그 포스트 목록 페이지."""
    return render(request, 'dashboard/blog/list.html', {'posts': Post.objects.all()})


@dashboard_required
def post_table_body(request: HttpRequest) -> HttpResponse:
    """블로그 포스트 목록 테이블 본문 (htmx 부분 응답)."""
    return render(request, 'dashboard/blog/_table_body.html', {'posts': Post.objects.all()})


@dashboard_required
def post_form(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    """블로그 포스트 생성/수정 폼 (htmx 부분 응답)."""
    post = get_object_or_404(Post, pk=pk) if pk else None

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return render(request, 'dashboard/blog/_table_body.html', {'posts': Post.objects.all()})
        return render(request, 'dashboard/blog/_form.html', {'form': form, 'post': post}, status=200)

    form = PostForm(instance=post)
    return render(request, 'dashboard/blog/_form.html', {'form': form, 'post': post})


@dashboard_required
@require_POST
def post_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """블로그 포스트 삭제 (htmx 부분 응답)."""
    post = get_object_or_404(Post, pk=pk)
    post.delete()
    return render(request, 'dashboard/blog/_table_body.html', {'posts': Post.objects.all()})


# --- 자동화 스케줄 제어 ---

def _automation_jobs() -> list[dict]:
    """JOB_DEFINITIONS 순서대로 각 잡의 현재 설정을 시딩·조회한다."""
    return [
        {'job_id': job_id, 'label': definition['label'], 'config': get_or_seed_job_config(job_id, definition)}
        for job_id, definition in JOB_DEFINITIONS.items()
    ]


@dashboard_required
def automation_list(request: HttpRequest) -> HttpResponse:
    """자동화 잡 목록 및 현재 설정 페이지."""
    return render(request, 'dashboard/automation/list.html', {
        'jobs': _automation_jobs(),
        'scheduler_running': get_scheduler() is not None,
    })


@dashboard_required
def automation_table_body(request: HttpRequest) -> HttpResponse:
    """자동화 잡 목록 테이블 본문 (htmx 부분 응답 — 취소 시 사용)."""
    return render(request, 'dashboard/automation/_table_body.html', {'jobs': _automation_jobs()})


@dashboard_required
def automation_form(request: HttpRequest, job_id: str) -> HttpResponse:
    """자동화 잡 실행 시각·활성화 수정 폼 (htmx 부분 응답)."""
    if job_id not in JOB_DEFINITIONS:
        raise Http404('등록되지 않은 자동화 작업입니다.')
    definition = JOB_DEFINITIONS[job_id]
    config = get_or_seed_job_config(job_id, definition)
    form = ScheduledJobConfigForm(initial={
        'is_enabled': config.is_enabled,
        'cron_hour': config.cron_hour,
        'cron_minute': config.cron_minute,
    })
    return render(request, 'dashboard/automation/_form.html', {
        'job_id': job_id, 'label': definition['label'], 'form': form,
    })


@dashboard_required
@require_POST
def automation_update(request: HttpRequest, job_id: str) -> HttpResponse:
    """자동화 잡 설정 저장 (htmx 부분 응답)."""
    if job_id not in JOB_DEFINITIONS:
        raise Http404('등록되지 않은 자동화 작업입니다.')

    # 목록/폼 화면을 거치지 않고 이 엔드포인트가 직접 호출될 수 있으므로,
    # update_job_schedule의 ScheduledJobConfig.objects.get() 호출 전에 설정 행 존재를 보장한다.
    get_or_seed_job_config(job_id, JOB_DEFINITIONS[job_id])

    form = ScheduledJobConfigForm(request.POST)
    if not form.is_valid():
        return render(request, 'dashboard/automation/_form.html', {
            'job_id': job_id, 'label': JOB_DEFINITIONS[job_id]['label'], 'form': form,
        }, status=200)

    update_job_schedule(
        job_id,
        is_enabled=form.cleaned_data['is_enabled'],
        hour=form.cleaned_data['cron_hour'],
        minute=form.cleaned_data['cron_minute'],
    )
    return render(request, 'dashboard/automation/_table_body.html', {'jobs': _automation_jobs()})
