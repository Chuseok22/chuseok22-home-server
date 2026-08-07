from apps.blog.models import Post


def update_post_content(post: Post, *, title: str, summary: str, content: str) -> Post:
    """블로그 포스트의 제목·요약·본문만 갱신한다. 사이트 인라인 편집 전용 — 그 외 필드는 건드리지 않는다."""
    post.title = title
    post.summary = summary
    post.content = content
    post.save(update_fields=['title', 'summary', 'content', 'updated_at'])
    return post
