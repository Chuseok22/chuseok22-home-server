from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.dashboard.decorators import dashboard_required


@dashboard_required
def home(request: HttpRequest) -> HttpResponse:
    """대시보드 홈. 하위 관리 화면으로 이동하는 진입점."""
    return render(request, 'dashboard/home.html')
