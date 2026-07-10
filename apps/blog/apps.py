from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'
    label = 'blog'

    def ready(self) -> None:
        from apps.blog import signals  # noqa: F401
