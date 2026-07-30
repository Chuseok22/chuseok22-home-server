from django import forms
from django.contrib import admin
from django.http import HttpRequest

from apps.restaurants.models import Restaurant, RestaurantSuggestion, RestaurantTag
from apps.restaurants.services.slug import generate_unique_slug


@admin.register(RestaurantTag)
class RestaurantTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def save_model(
        self, request: HttpRequest, obj: RestaurantTag, form: forms.ModelForm, change: bool,
    ) -> None:
        if not obj.slug:
            obj.slug = generate_unique_slug(RestaurantTag, obj.name)
        super().save_model(request, obj, form, change)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'meal_time', 'personal_rating', 'updated_at')
    list_filter = ('meal_time', 'tags')
    search_fields = ('name', 'address', 'road_address')
    autocomplete_fields = ('tags',)
    fieldsets = (
        ('카카오 검색', {
            'fields': ('name', 'address', 'road_address', 'latitude', 'longitude', 'category', 'kakao_place_url'),
        }),
        ('큐레이션', {
            'fields': ('tags', 'meal_time', 'personal_rating', 'personal_review', 'note'),
        }),
    )


@admin.register(RestaurantSuggestion)
class RestaurantSuggestionAdmin(admin.ModelAdmin):
    list_display = ('restaurant_name', 'submitted_by', 'is_reviewed', 'created_at')
    list_filter = ('is_reviewed',)
    search_fields = ('restaurant_name', 'message')
