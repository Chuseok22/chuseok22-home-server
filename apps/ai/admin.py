from django import forms
from django.contrib import admin

from apps.ai.models import PromptTemplate
from apps.ai.services.model_catalog import get_model_choices


class PromptTemplateForm(forms.ModelForm):
    # model 필드는 기본적으로 자유 입력 CharField이지만, SUH-AIder에 실제 등록된 모델
    # 목록에서만 고르도록 그룹핑된 드롭다운으로 오버라이드한다. choices는 __init__에서
    # 동적으로 채운다(모듈 로드 시점이 아니라 폼 인스턴스 생성 시점에 최신 목록을 반영하기 위함).
    model = forms.ChoiceField(choices=[], widget=forms.Select, label='SUH-AIder 모델명')

    class Meta:
        model = PromptTemplate
        fields = '__all__'

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        choices = get_model_choices()
        catalog_fetch_failed = not choices

        # 기존에 저장된 model 값이 최신 목록에 없으면(서버에서 모델이 삭제됐거나 조회
        # 실패) 저장이 막히지 않도록 임시 선택지로 끼워 넣는다.
        current = self.instance.model if self.instance and self.instance.pk else None
        flat_values = {value for _, options in choices for value, _ in options}
        if current and current not in flat_values:
            choices = [('현재 값 (목록에 없음)', [(current, current)])] + choices

        self.fields['model'].choices = choices
        if catalog_fetch_failed:
            self.fields['model'].help_text = (
                'SUH-AIder 서버에 연결할 수 없어 모델 목록을 불러오지 못했습니다.'
            )


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    form = PromptTemplateForm
    list_display = ('feature', 'name', 'model', 'is_active', 'updated_at')
    list_filter = ('feature', 'is_active')
    search_fields = ('name', 'system_prompt')
