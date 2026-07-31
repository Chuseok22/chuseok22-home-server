from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from apps.ai.services.suh_aider_client import SuhAiderClient, SuhAiderClientError


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


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-api-key')
class TestSuhAiderClientErrors(TestCase):
    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_비2xx_응답시_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        for status_code in (401, 403, 404, 500, 502, 503):
            with self.subTest(status_code=status_code):
                mock_response = MagicMock()
                mock_response.status_code = status_code
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                    f'{status_code} Client/Server Error', response=mock_response
                )
                mock_post.return_value = mock_response

                client = SuhAiderClient()
                with self.assertRaises(SuhAiderClientError):
                    client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_타임아웃시_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout('read timed out')

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_네트워크_연결_오류시_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError('connection refused')

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_응답에_message_키_없을때_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'model': 'functiongemma', 'done': True}
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_응답의_message에_content_키_없을때_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'model': 'functiongemma', 'message': {'role': 'assistant'}, 'done': True}
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_message가_예상과_다른_타입일때_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'model': 'functiongemma', 'message': 'not-a-dict', 'done': True}
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.chat(model='functiongemma', messages=[{'role': 'user', 'content': '안녕'}])


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-api-key')
class TestSuhAiderClientListModels(TestCase):
    @patch('apps.ai.services.suh_aider_client.requests.get')
    def test_정상_응답시_모델_목록_반환(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'functiongemma:latest', 'details': {'parameter_size': '268.10M'}},
                {'name': 'qwen3-embedding:4b', 'details': {'parameter_size': '4.0B'}},
            ]
        }
        mock_get.return_value = mock_response

        client = SuhAiderClient()
        result = client.list_models()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'functiongemma:latest')
        mock_get.assert_called_once_with(
            'https://ai.example.com/api/tags',
            headers={'X-API-Key': 'test-api-key'},
            timeout=(5, 60),
        )

    @patch('apps.ai.services.suh_aider_client.requests.get')
    def test_네트워크_오류시_SuhAiderClientError_발생(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError('connection refused')

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.list_models()

    @patch('apps.ai.services.suh_aider_client.requests.get')
    def test_응답에_models_키_없을때_SuhAiderClientError_발생(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.list_models()


@override_settings(SUH_AIDER_BASE_URL='https://ai.example.com', SUH_AIDER_API_KEY='test-api-key')
class TestSuhAiderClientGetModelCapabilities(TestCase):
    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_정상_응답시_capabilities_반환(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'capabilities': ['completion', 'tools']}
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        result = client.get_model_capabilities('functiongemma:latest')

        self.assertEqual(result, ['completion', 'tools'])
        mock_post.assert_called_once_with(
            'https://ai.example.com/api/show',
            headers={'Content-Type': 'application/json', 'X-API-Key': 'test-api-key'},
            json={'model': 'functiongemma:latest'},
            timeout=(5, 60),
        )

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_네트워크_오류시_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError('connection refused')

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.get_model_capabilities('functiongemma:latest')

    @patch('apps.ai.services.suh_aider_client.requests.post')
    def test_응답에_capabilities_키_없을때_SuhAiderClientError_발생(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        client = SuhAiderClient()
        with self.assertRaises(SuhAiderClientError):
            client.get_model_capabilities('functiongemma:latest')
