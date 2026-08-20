from django.core.management.base import BaseCommand, CommandParser

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import CLUB_RECRUITMENT_DETECTION_FEATURE

_PROMPT_NAME = '동아리 모집 여부 판별 프롬프트'
_DEFAULT_MODEL = 'gemma4:e4b'

_SYSTEM_PROMPT = """
[역할]
당신은 대학생 IT 연합동아리의 공식 홈페이지 본문 텍스트를 읽고, 지금 신입 기수 모집이 진행
중인지 판별하는 어시스턴트입니다.

[출력 형식]
다른 설명 없이, 아래 필드만 담은 JSON 객체 하나만 출력합니다.
{
  "is_recruiting": true 또는 false,
  "application_start": "YYYY-MM-DD" 또는 null,
  "application_end": "YYYY-MM-DD" 또는 null,
  "apply_url": "지원 링크 URL" 또는 null,
  "evidence_quote": "모집 중이라고 판단한 근거가 되는, 본문에 실제로 있는 문장을 그대로 인용" 또는 null
}

[판별 원칙]
- 본문에 "모집", "지원자 모집", "N기 모집" 등 현재 진행 중인 모집을 알리는 문구가 있어야
  is_recruiting을 true로 판단합니다. 과거 기수 소개, 활동 후기, 모집 예정 안내(아직 시작 전)만
  있는 경우 false로 판단합니다.
- evidence_quote는 반드시 본문에 실제로 등장하는 문장을 그대로 복사해야 합니다. 요약하거나
  재구성하지 않습니다. is_recruiting이 false면 evidence_quote는 null로 둡니다.
- 날짜를 알 수 없으면 application_start/application_end를 null로 둡니다. 날짜를 추측해서
  채우지 않습니다.
- 본문에 지원 링크(구글폼, 지원 페이지 등)가 명시돼 있지 않으면 apply_url을 null로 둡니다.
""".strip()


class Command(BaseCommand):
    help = (
        '동아리 모집 여부 판별용 시스템 프롬프트를 최초 1회 부트스트랩한다. '
        f'이미 "{_PROMPT_NAME}" 레코드가 있으면 문구만 갱신하고 model은 보존한다.'
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--model', default=_DEFAULT_MODEL,
            help=f'레코드가 없어서 새로 생성할 때만 사용할 SUH-AIder 모델명 (기본값: {_DEFAULT_MODEL})',
        )

    def handle(self, *args: object, **options: object) -> None:
        model = options['model']
        template = PromptTemplate.objects.filter(
            feature=CLUB_RECRUITMENT_DETECTION_FEATURE, name=_PROMPT_NAME,
        ).first()

        if template is None:
            PromptTemplate.objects.create(
                feature=CLUB_RECRUITMENT_DETECTION_FEATURE, name=_PROMPT_NAME,
                system_prompt=_SYSTEM_PROMPT, model=model, is_active=True,
            )
            self.stdout.write(f'[생성] "{_PROMPT_NAME}" 프롬프트를 새로 만들고 활성화했습니다 (model={model}).')
            return

        template.system_prompt = _SYSTEM_PROMPT
        template.is_active = True
        template.save()
        self.stdout.write(f'[갱신] "{_PROMPT_NAME}" 프롬프트 문구를 갱신했습니다 (model={template.model}, 기존 값 유지).')
