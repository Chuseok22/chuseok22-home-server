from django import forms
from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path

from apps.places.models import Place, PlaceSuggestion, PlaceTag
from apps.places.services.kakao import KakaoApiError, search_places
from apps.places.services.slug import generate_unique_slug


@admin.register(PlaceTag)
class PlaceTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def save_model(
        self, request: HttpRequest, obj: PlaceTag, form: forms.ModelForm, change: bool,
    ) -> None:
        if not obj.slug:
            obj.slug = generate_unique_slug(PlaceTag, obj.name)
        super().save_model(request, obj, form, change)


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'kakao_category', 'meal_time', 'personal_rating', 'updated_at')
    list_filter = ('category', 'meal_time', 'tags')
    search_fields = ('name', 'address', 'road_address')
    autocomplete_fields = ('tags',)
    fieldsets = (
        ('카카오 검색', {
            'fields': (
                'name', 'address', 'road_address', 'latitude', 'longitude',
                'kakao_category', 'kakao_place_url', 'kakao_place_id',
            ),
        }),
        ('큐레이션', {
            'fields': ('category', 'tags', 'meal_time', 'personal_rating', 'personal_review', 'note'),
        }),
    )

    class Media:
        js = ('places/admin/kakao_search.js',)

    def get_urls(self) -> list:
        custom_urls = [
            path(
                'kakao-search/',
                self.admin_site.admin_view(self.kakao_search_view),
                name='places_place_kakao_search',
            ),
        ]
        return custom_urls + super().get_urls()

    def kakao_search_view(self, request: HttpRequest) -> JsonResponse:
        # admin_view()는 로그인·staff 여부만 검사하므로, Place 변경 권한이 없는
        # staff 계정의 검색을 막으려면 모델 단위 권한을 별도로 확인해야 한다.
        # 검색 위젯은 추가(add) 화면에도 노출되므로 change 권한만 검사하면 add 권한만
        # 가진 staff 계정이 403을 받는다 — 두 권한 중 하나라도 있으면 허용한다.
        if not (self.has_change_permission(request) or self.has_add_permission(request)):
            return JsonResponse({'success': False, 'error_message': '권한이 없습니다.'}, status=403)

        query = request.GET.get('query', '').strip()
        if not query:
            return JsonResponse({'success': False, 'error_message': '검색어를 입력해주세요.'}, status=400)

        try:
            results = search_places(query)
        except KakaoApiError as exc:
            return JsonResponse({'success': False, 'error_message': str(exc)}, status=502)

        return JsonResponse({
            'success': True,
            'results': [
                {
                    'name': result.name,
                    'address': result.address,
                    'road_address': result.road_address,
                    'latitude': result.latitude,
                    'longitude': result.longitude,
                    'category': result.category,
                    'place_url': result.place_url,
                }
                for result in results
            ],
        })


@admin.register(PlaceSuggestion)
class PlaceSuggestionAdmin(admin.ModelAdmin):
    list_display = ('restaurant_name', 'submitted_by', 'is_reviewed', 'created_at')
    list_filter = ('is_reviewed',)
    search_fields = ('restaurant_name', 'message')
