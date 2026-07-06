from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.dashboard.decorators import dashboard_required
from apps.dashboard.forms import ProjectForm
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
