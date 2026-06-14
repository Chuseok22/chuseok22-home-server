from django.contrib import admin

from .models import GithubActivity


@admin.register(GithubActivity)
class GithubActivityAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'repo_name', 'title', 'occurred_at', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('repo_name', 'title')
    readonly_fields = ('created_at',)
