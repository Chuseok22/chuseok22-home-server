from dataclasses import dataclass

from django.db.models import Count, Q, QuerySet

from apps.blog.models import Category, Post


class CategoryNotFoundError(Exception):
    """이름과 일치하는 카테고리가 없을 때 발생한다."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"카테고리 '{name}'을 찾을 수 없습니다.")


def get_category_by_name(name: str) -> Category:
    """이름으로 기존 카테고리를 조회한다. 대분류/소분류 구분 없이 그대로 사용한다."""
    try:
        return Category.objects.get(name=name)
    except Category.DoesNotExist:
        raise CategoryNotFoundError(name) from None


@dataclass(frozen=True)
class CategorySidebarItem:
    """사이드바 표시용 카테고리 항목. children은 대분류에서만 채워진다."""

    name: str
    slug: str
    post_count: int
    children: tuple['CategorySidebarItem', ...] = ()


def get_category_sidebar_items() -> list[CategorySidebarItem]:
    """공개(is_published=True) 글이 1개 이상 있는 카테고리만 반환한다.
    대분류 post_count는 직속 글 + 소분류 글 합계, 소분류 post_count는 직속 글만 센다.
    """
    categories = Category.objects.annotate(
        own_count=Count('posts', filter=Q(posts__is_published=True)),
    ).order_by('name')

    children_by_parent_id: dict[int, list[Category]] = {}
    top_level: list[Category] = []
    for category in categories:
        if category.parent_id is None:
            top_level.append(category)
        else:
            children_by_parent_id.setdefault(category.parent_id, []).append(category)

    items: list[CategorySidebarItem] = []
    for parent in top_level:
        children = children_by_parent_id.get(parent.id, [])
        visible_children = tuple(
            CategorySidebarItem(name=child.name, slug=child.slug, post_count=child.own_count)
            for child in children
            if child.own_count > 0
        )
        combined_count = parent.own_count + sum(child.own_count for child in children)
        if combined_count == 0:
            continue
        items.append(
            CategorySidebarItem(
                name=parent.name,
                slug=parent.slug,
                post_count=combined_count,
                children=visible_children,
            ),
        )
    return items


def filter_published_posts_by_category_slug(category_slug: str | None) -> QuerySet[Post]:
    """category_slug가 없으면 전체 공개 글을 반환한다.
    대분류 slug면 그 대분류 + 소속 소분류 전체 공개 글을,
    소분류 slug면 그 소분류 공개 글만 반환한다.
    존재하지 않는 slug면 빈 QuerySet을 반환한다.
    """
    posts = Post.objects.filter(is_published=True).prefetch_related('tags')
    if category_slug is None:
        return posts

    try:
        category = Category.objects.get(slug=category_slug)
    except Category.DoesNotExist:
        return posts.none()

    if category.parent_id is None:
        return posts.filter(Q(category=category) | Q(category__parent=category))
    return posts.filter(category=category)
