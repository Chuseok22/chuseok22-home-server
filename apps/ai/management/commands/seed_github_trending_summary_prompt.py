from django.core.management.base import BaseCommand, CommandParser

from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import GITHUB_TRENDING_SUMMARY_FEATURE

_PROMPT_NAME = 'GitHub 트렌딩 요약 프롬프트'
_DEFAULT_MODEL = 'functiongemma'

_SYSTEM_PROMPT = """
[역할]
당신은 오픈소스 저장소의 README를 읽고 핵심을 파악해 한국어로 간결하게 소개하는 어시스턴트입니다.

[원칙]
- README 원문이 영어 등 다른 언어여도, 답변은 반드시 한국어로 작성합니다.
- 이 저장소가 무엇을 하는 프로젝트인지, 어떤 문제를 해결하는지를 중심으로 2~3문장으로 요약합니다.
- 배지, 설치 명령어, 라이선스 문구, 목차 등 README의 장식적/절차적 요소는 요약에서 제외합니다.
- 근거 없는 평가나 홍보성 문구를 덧붙이지 않고, README에 실제로 담긴 내용만 사실대로 전달합니다.
- 요약 문장 외에 다른 안내 문구(예: "다음은 요약입니다")를 덧붙이지 않고, 요약 본문만 출력합니다.
""".strip()


class Command(BaseCommand):
    help = (
        'GitHub 트렌딩 리포트용 README 요약 시스템 프롬프트를 최초 1회 부트스트랩한다. '
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
            feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME,
        ).first()

        if template is None:
            PromptTemplate.objects.create(
                feature=GITHUB_TRENDING_SUMMARY_FEATURE, name=_PROMPT_NAME,
                system_prompt=_SYSTEM_PROMPT, model=model, is_active=True,
            )
            self.stdout.write(f'[생성] "{_PROMPT_NAME}" 프롬프트를 새로 만들고 활성화했습니다 (model={model}).')
            return

        template.system_prompt = _SYSTEM_PROMPT
        template.is_active = True
        template.save()
        self.stdout.write(f'[갱신] "{_PROMPT_NAME}" 프롬프트 문구를 갱신했습니다 (model={template.model}, 기존 값 유지).')
