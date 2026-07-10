from django.contrib import admin

from .models import GithubActivity, GithubContributionDay, GithubProfileStats


@admin.register(GithubActivity)
class GithubActivityAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'repo_name', 'title', 'occurred_at', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('repo_name', 'title')
    readonly_fields = ('created_at',)


@admin.register(GithubContributionDay)
class GithubContributionDayAdmin(admin.ModelAdmin):
    list_display = ('date', 'contribution_count')
    ordering = ('-date',)


@admin.register(GithubProfileStats)
class GithubProfileStatsAdmin(admin.ModelAdmin):
    list_display = ('total_stars', 'updated_at')
    readonly_fields = ('updated_at',)
