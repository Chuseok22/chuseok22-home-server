from django.contrib import admin

from apps.site.models import Tool


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_owner_only', 'order')
    list_editable = ('order',)
