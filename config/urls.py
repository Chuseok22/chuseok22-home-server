from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Core
    path('api/v1/', include('apps.core.urls')),

    # JWT 인증 (기존 API 전용)
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 학술정보원 (기존 REST API — 서비스 레이어는 apps.site가 재사용, 엔드포인트는 유지)
    path('api/v1/library/', include('apps.sejong.library.urls')),

    # GitHub 활동
    path('api/v1/activities/', include('apps.activity.urls')),

    # 세종대 학생 조회 (기존 REST API)
    path('api/v1/sejong/students/', include('apps.sejong.student.urls')),

    # Swagger (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 소셜 로그인 (django-allauth)
    path('accounts/', include('allauth.urls')),

    # 댓글·좋아요
    path('engagement/', include('apps.engagement.urls')),

    # 커스텀 관리자 대시보드
    path('dashboard/', include('apps.dashboard.urls')),

    # 공개 사이트 (SSR) — 항상 마지막에 배치
    path('', include('apps.site.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
