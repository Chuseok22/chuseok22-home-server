from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sejong.library'
    label = 'library'  # app_label 유지 — 기존 migration 기록 보존
    verbose_name = '학술정보원'
