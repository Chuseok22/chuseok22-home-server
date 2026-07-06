from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.engagement.models import Comment, Like

# 댓글·좋아요를 붙일 수 있는 모델 화이트리스트. (app_label, model) 형태.
# User, ReservationHistory 등 다른 모델에 임의로 붙는 것과 PK 존재 여부 탐침을 막는다.
_ALLOWED_TARGET_MODELS = {
    ('blog', 'post'),
    ('projects', 'project'),
    ('site', 'tool'),
}

_MAX_COMMENT_LENGTH = 1000


def _resolve_target(app_label: str, model: str, object_id: int) -> tuple[ContentType, Model]:
    if (app_label, model) not in _ALLOWED_TARGET_MODELS:
        raise Http404('댓글·좋아요를 지원하지 않는 대상입니다.')
    content_type = get_object_or_404(ContentType, app_label=app_label, model=model)
    target = get_object_or_404(content_type.model_class(), pk=object_id)
    return content_type, target


@login_required
@require_POST
def comment_create(request: HttpRequest, app_label: str, model: str, object_id: int) -> HttpResponse:
    """댓글 작성 (htmx 부분 응답으로 갱신된 댓글 목록 반환). 검증 실패 시 에러 메시지를 함께 반환한다."""
    content_type, target = _resolve_target(app_label, model, object_id)
    body = request.POST.get('body', '').strip()

    error = None
    if not body:
        error = '댓글 내용을 입력해주세요.'
    elif len(body) > _MAX_COMMENT_LENGTH:
        error = f'댓글은 최대 {_MAX_COMMENT_LENGTH}자까지 입력할 수 있습니다.'
    else:
        Comment.objects.create(content_type=content_type, object_id=target.pk, author=request.user, body=body)

    comments = Comment.objects.filter(content_type=content_type, object_id=target.pk).select_related('author')
    return render(request, 'engagement/comments.html', {'comments': comments, 'target': target, 'error': error})


@login_required
@require_POST
def like_toggle(request: HttpRequest, app_label: str, model: str, object_id: int) -> HttpResponse:
    """좋아요 토글 (htmx 부분 응답으로 갱신된 좋아요 수 반환)."""
    content_type, target = _resolve_target(app_label, model, object_id)
    # get_or_create는 동시 요청으로 create가 IntegrityError를 만나도 내부적으로 재조회해 반환하므로
    # unique_like_per_user_per_target 제약과 결합한 레이스 컨디션을 원자적으로 처리한다.
    like, created = Like.objects.get_or_create(
        content_type=content_type, object_id=target.pk, user=request.user,
    )
    if not created:
        like.delete()

    like_count = Like.objects.filter(content_type=content_type, object_id=target.pk).count()
    is_liked = Like.objects.filter(content_type=content_type, object_id=target.pk, user=request.user).exists()
    return render(
        request,
        'engagement/like_button.html',
        {'target': target, 'like_count': like_count, 'is_liked': is_liked},
    )
