from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.ai.services.suh_aider_client import SuhAiderClient


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-api-key')
class TestSuhAiderClientChat(TestCase):
    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_정상_응답시_assistant_텍스트_반환(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'model': 'functiongemma',
            'message': {'role': 'assistant', 'content': '안녕하세요'},
            'done': True,
        }
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        result = client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

        self.assertEqual(result, '안녕하세요')
        mock_post.assert_called_once_with(
            'https://ai.example.com/api/chat',
            headers={'Content-Type': 'application/json', 'X-API-Key': 'test-api-key'},
            json={
                'model': 'functiongemma',
                'messages': [{'role': 'user', 'content': '안녕'}],
                'stream': False,
            },
            timeout=(5, 60),
        )
