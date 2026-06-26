from django.apps import AppConfig


class StudentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sejong.student'
    label = 'sejong_student'
    verbose_name = '세종대 학생 조회'
