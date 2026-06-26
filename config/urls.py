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

    # JWT 인증
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 학술정보원
    path('api/v1/library/', include('apps.sejong.library.urls')),

    # GitHub 활동
    path('api/v1/activities/', include('apps.activity.urls')),

    # 프로젝트
    path('api/v1/projects/', include('apps.projects.urls')),

    # 세종대 학생 조회
    path('api/v1/sejong/students/', include('apps.sejong.student.urls')),

    # Swagger (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
