from django.contrib import admin

from .models import SejongAccount


@admin.register(SejongAccount)
class SejongAccountAdmin(admin.ModelAdmin):
    list_display = ('label', 'student_id')
