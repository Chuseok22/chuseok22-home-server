from django.contrib import admin

from apps.ai.models import PromptTemplate


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('feature', 'name', 'model', 'is_active', 'updated_at')
    list_filter = ('feature', 'is_active')
    search_fields = ('name', 'system_prompt')
