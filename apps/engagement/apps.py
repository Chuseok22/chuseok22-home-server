from django.apps import AppConfig


class EngagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.engagement'
    label = 'engagement'

    def ready(self) -> None:
        from apps.engagement import signals  # noqa: F401
