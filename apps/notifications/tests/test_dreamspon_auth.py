from unittest.mock import patch

import requests
from django.test import TestCase, override_settings

from apps.notifications.crawlers.dreamspon_auth import DreamsponAuth, DreamsponSession


class TestDreamsponAuthInit(TestCase):
    @override_settings(DREAMSPON_ID='', DREAMSPON_PASSWORD='')
    def test_자격증명_미설정시_예외(self) -> None:
        with self.assertRaises(ValueError):
            DreamsponAuth()

    @override_settings(DREAMSPON_ID='test@example.com', DREAMSPON_PASSWORD='')
    def test_비밀번호만_미설정시_예외(self) -> None:
        with self.assertRaises(ValueError):
            DreamsponAuth()

    @override_settings(DREAMSPON_ID='test@example.com', DREAMSPON_PASSWORD='pw1234')
    def test_자격증명_설정시_정상_생성(self) -> None:
        auth = DreamsponAuth()
        self.assertEqual(auth._user_id, 'test@example.com')
        self.assertEqual(auth._password, 'pw1234')


@override_settings(DREAMSPON_ID='test@example.com', DREAMSPON_PASSWORD='pw1234')
class TestDreamsponAuthLogin(TestCase):
    def test_로그인_성공시_세션_반환(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {
                'result': True, 'checkyn': 'Y', 'pageLink': '/',
            }
            result = DreamsponAuth().login()

        self.assertIsInstance(result, DreamsponSession)
        self.assertIsNotNone(result.session)

    def test_자격증명_불일치시_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {'result': True, 'checkyn': 'N'}
            result = DreamsponAuth().login()

        self.assertIsNone(result)

    def test_result_false시_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {'result': False}
            result = DreamsponAuth().login()

        self.assertIsNone(result)

    def test_요청_실패시_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.RequestException('연결 실패')
            result = DreamsponAuth().login()

        self.assertIsNone(result)

    def test_json_파싱_실패시_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.side_effect = ValueError('invalid json')
            result = DreamsponAuth().login()

        self.assertIsNone(result)

    def test_응답이_배열인_경우_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = ['unexpected', 'array']
            result = DreamsponAuth().login()

        self.assertIsNone(result)

    def test_응답이_null인_경우_None(self) -> None:
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = None
            result = DreamsponAuth().login()

        self.assertIsNone(result)
