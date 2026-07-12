from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.ai.services.suh_aider_client import SuhAiderClientError


class TestCheckSuhAiderConnection(TestCase):
    @patch('apps.ai.management.commands.check_suh_aider_connection.SuhAiderClient')
    def test_연결_성공시_응답_출력(self, mock_client_class: MagicMock) -> None:
        mock_client_class.return_value.chat.return_value = '안녕하세요'
        out = StringIO()

        call_command('check_suh_aider_connection', model='functiongemma', message='안녕', stdout=out)

        self.assertIn('SUH-AIder 연결 성공', out.getvalue())
        self.assertIn('안녕하세요', out.getvalue())

    @patch('apps.ai.management.commands.check_suh_aider_connection.SuhAiderClient')
    def test_연결_실패시_에러_출력(self, mock_client_class: MagicMock) -> None:
        mock_client_class.return_value.chat.side_effect = SuhAiderClientError('인증 실패')
        out = StringIO()
        err = StringIO()

        call_command('check_suh_aider_connection', stdout=out, stderr=err)

        self.assertIn('SUH-AIder 연결 실패', err.getvalue())
