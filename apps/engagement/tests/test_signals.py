from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.blog.models import Post
from apps.engagement.models import Comment, Like

User = get_user_model()


@pytest.mark.django_db
def test_댓글_생성시_관리자_알림_발송() -> None:
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')

    with patch('apps.engagement.signals.TelegramService.send_admin_alert') as mock_alert:
        Comment.objects.create(target=post, author=user, body='좋은 글이네요')

    mock_alert.assert_called_once()
    assert '좋은 글이네요' in mock_alert.call_args.args[0]


@pytest.mark.django_db
def test_좋아요_생성시_관리자_알림_발송() -> None:
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')

    with patch('apps.engagement.signals.TelegramService.send_admin_alert') as mock_alert:
        Like.objects.create(target=post, user=user)

    mock_alert.assert_called_once()
