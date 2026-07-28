from django.contrib import admin

from .models import Notice, NoticeSource


@admin.register(NoticeSource)
class NoticeSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'crawler_type', 'url', 'is_active', 'has_webhook', 'created_at')
    list_filter = ('is_active', 'crawler_type')
    search_fields = ('name',)

    @admin.display(boolean=True, description='웹훅 설정')
    def has_webhook(self, obj: NoticeSource) -> bool:
        return bool(obj.discord_webhook_url)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'is_notified', 'notified_at', 'created_at')
    list_filter = ('is_notified', 'source')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'notified_at')
