import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError

from apps.blog.models import Post

User = get_user_model()


@pytest.mark.django_db
def test_comment은_임의의_모델에_연결_가능하다() -> None:
    from apps.engagement.models import Comment

    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')

    comment = Comment.objects.create(target=post, author=user, body='좋은 글이네요')

    assert comment.content_type == ContentType.objects.get_for_model(Post)
    assert comment.target == post


@pytest.mark.django_db
def test_like는_동일_사용자가_동일_대상에_중복_불가() -> None:
    from apps.engagement.models import Like

    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')

    Like.objects.create(target=post, user=user)

    with pytest.raises(IntegrityError):
        Like.objects.create(target=post, user=user)
