from django.core.management.base import BaseCommand, CommandParser

from apps.ai.services.suh_aider_client import SuhAiderClient, SuhAiderClientError


class Command(BaseCommand):
    help = 'SUH-AIder AI 서버와의 연결 상태를 수동으로 점검한다 (개발 진단용)'

    def add_arguments(self, parser: CommandParser) -> None:
        # 기본값 'functiongemma'는 eodaego-AI 실사용 예시 기준(가이드 문서 2절) — 실제 SUH-AIder 서버에
        # 등록된 모델명이 다르면 --model로 재정의해서 사용한다.
        parser.add_argument('--model', type=str, default='functiongemma', help='호출할 모델명')
        parser.add_argument('--message', type=str, default='안녕', help='전송할 테스트 메시지')

    def handle(self, *args, **options) -> None:
        client = SuhAiderClient()
        try:
            content = client.chat(
                model=options['model'],
                messages=[{'role': 'user', 'content': options['message']}],
            )
        except SuhAiderClientError as exc:
            self.stderr.write(f'SUH-AIder 연결 실패: {exc}')
            return

        self.stdout.write(f'SUH-AIder 연결 성공 (model={options["model"]})')
        self.stdout.write(f'응답: {content}')
