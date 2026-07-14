import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from apps.blog.models import Post
from apps.engagement.models import Comment, Like

User = get_user_model()


@pytest.mark.django_db
def test_비로그인_사용자는_댓글_작성_불가() -> None:
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.post(url, {'body': '댓글입니다'})

    assert response.status_code == 302  # 로그인 페이지로 리다이렉트
    assert Comment.objects.count() == 0


@pytest.mark.django_db
def test_로그인_사용자는_댓글_작성_가능() -> None:
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.post(url, {'body': '댓글입니다'})

    assert response.status_code == 200
    assert Comment.objects.filter(content_type=content_type, object_id=post.pk, body='댓글입니다').exists()


@pytest.mark.django_db
def test_좋아요_토글() -> None:
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:like-toggle', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})

    response = client.post(url)
    assert Like.objects.filter(content_type=content_type, object_id=post.pk, user=user).exists()

    response = client.post(url)
    assert not Like.objects.filter(content_type=content_type, object_id=post.pk, user=user).exists()


@pytest.mark.django_db
def test_화이트리스트에_없는_모델은_404() -> None:
    """User 등 화이트리스트 밖 모델에는 댓글/좋아요를 붙일 수 없다."""
    user = User.objects.create_user(username='reader')
    other_user = User.objects.create_user(username='target')
    content_type = ContentType.objects.get_for_model(User)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': other_user.pk})
    response = client.post(url, {'body': '댓글입니다'})

    assert response.status_code == 404
    assert Comment.objects.count() == 0


@pytest.mark.django_db
def test_최대_길이를_초과한_댓글은_저장되지_않는다() -> None:
    """htmx 응답 특성상 검증 실패도 200을 반환하되, 댓글은 저장되지 않고 에러 메시지가 표시되어야 한다."""
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    too_long_body = 'a' * 1001  # _MAX_COMMENT_LENGTH(1000)보다 1자 초과
    response = client.post(url, {'body': too_long_body})

    assert response.status_code == 200
    assert Comment.objects.count() == 0
    assert '최대 1000자까지' in response.content.decode()


@pytest.mark.django_db
def test_빈_댓글은_에러_메시지와_함께_200_반환() -> None:
    """본문이 비어 있으면 저장하지 않고, htmx가 swap할 수 있도록 200 + 에러 메시지로 반환한다."""
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.post(url, {'body': '   '})

    assert response.status_code == 200
    assert Comment.objects.count() == 0
    assert '댓글 내용을 입력해주세요' in response.content.decode()


@pytest.mark.django_db
def test_비로그인_사용자는_좋아요_토글_불가() -> None:
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    url = reverse('engagement:like-toggle', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.post(url)

    assert response.status_code == 302  # 로그인 페이지로 리다이렉트
    assert Like.objects.count() == 0


@pytest.mark.django_db
def test_댓글_작성은_GET으로_호출할_수_없다() -> None:
    """상태를 변경하는 엔드포인트이므로 GET 요청은 거부되어야 한다."""
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.get(url)

    assert response.status_code == 405


@pytest.mark.django_db
def test_좋아요_토글은_GET으로_호출할_수_없다() -> None:
    """상태를 변경하는 엔드포인트이므로 GET 요청은 거부되어야 한다."""
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:like-toggle', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.get(url)

    assert response.status_code == 405


@pytest.mark.django_db
def test_존재하지_않는_object_id는_404() -> None:
    user = User.objects.create_user(username='reader')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:comment-create', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': 999999})
    response = client.post(url, {'body': '댓글입니다'})

    assert response.status_code == 404


@pytest.mark.django_db
def test_좋아요_버튼은_요청_중_비활성화_속성과_스피너를_포함한다() -> None:
    user = User.objects.create_user(username='reader')
    post = Post.objects.create(title='글', slug='post', content='...')
    content_type = ContentType.objects.get_for_model(Post)

    client = Client()
    client.force_login(user)
    url = reverse('engagement:like-toggle', kwargs={'app_label': content_type.app_label, 'model': content_type.model, 'object_id': post.pk})
    response = client.post(url)
    body = response.content.decode()

    assert 'hx-disabled-elt="this"' in body
    assert 'id="like-spinner"' in body
    assert 'loading-spinner' in body
