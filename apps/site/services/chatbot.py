import re
from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.db.models import Q
from django.urls import reverse

from apps.ai.services.prompt_template import CHATBOT_FEATURE, get_active_prompt
from apps.ai.services.suh_aider_client import SuhAiderClient
from apps.blog.models import Post
from apps.profile.models import Activity, Career, Certification, Profile, PullRequestHighlight, Skill
from apps.projects.models import Project

_MAX_HISTORY_TURNS = 10
_SEARCH_RESULT_LIMIT = 3
_MIN_TOKEN_LENGTH = 2
# 경력/자격증/대외활동/대표 PR은 Project/Post와 달리 토큰 검색으로 걸러지지 않고
# Profile 섹션처럼 항상 포함한다("경력이 어떻게 되나요?" 같은 메타 질문은 키워드가
# 데이터 자체에 들어있지 않아 검색으로 못 잡기 때문). 대신 프롬프트 크기가 무한정
# 커지지 않도록 각 섹션을 상위 N개로 캡한다.
_STATIC_SECTION_LIMIT = 5
# 토큰 수가 많을수록 Project/Post/Skill 각각에서 OR로 묶인 icontains 절이 그만큼 늘어나므로,
# 인증 없이 호출 가능한(rate limit은 있지만) 공개 엔드포인트에서 과도한 쿼리 비용이 발생하지
# 않도록 검색에 사용할 토큰 수를 제한한다.
_MAX_TOKENS = 20
# 공백/구두점 기준으로만 나누는 러프한 토큰화 — 한국어 조사가 붙은 형태("프로젝트에")는 그대로
# 하나의 토큰이 되므로 완벽하지 않지만, 형태소 분석 없이 "관련 있을 법한 항목을 놓치지 않는" 목적에는
# 충분하다고 판단했다(스펙의 "간단한 검색" 합의 사항).
_TOKEN_PATTERN = re.compile(r'[^\w가-힣]+')


class ChatbotConfigError(Exception):
    """챗봇용 활성 프롬프트가 설정되지 않았을 때 발생한다."""


@dataclass(frozen=True)
class ChatLink:
    """챗봇 답변에 함께 보여줄 추천 링크(버튼) 하나."""

    label: str
    url: str


@dataclass(frozen=True)
class ChatReply:
    """get_chat_reply()의 반환값. 답변 본문과 추천 링크를 함께 담는다."""

    text: str
    links: list[ChatLink]


def _project_recommendation_link(project: Project) -> ChatLink:
    """프로젝트를 대표하는 링크 하나를 우선순위대로 골라 ChatLink로 반환한다.

    title_href → web_site_href → github_href 순으로 첫 번째 non-empty 값을 쓰고,
    셋 다 없으면 프로젝트 목록 페이지로 폴백한다. project_card.html에서 title_href를
    프로젝트의 대표 링크로 쓰는 기존 관례를 그대로 따른다.
    """
    if project.title_href:
        return ChatLink(label=f'{project.title} ↗', url=project.title_href)
    if project.web_site_href:
        return ChatLink(label=f'{project.title} ↗', url=project.web_site_href)
    if project.github_href:
        return ChatLink(label=f'{project.title} ↗', url=project.github_href)
    return ChatLink(label='프로젝트 목록 →', url=reverse('site:projects'))


def get_chat_reply(user_message: str, history: list[dict[str, str]]) -> ChatReply:
    """활성 프롬프트 + 동적 컨텍스트(프로필/프로젝트/블로그/기술스택)를 조합해 SUH-AIder 응답과 추천 링크를 반환한다."""
    template = get_active_prompt(CHATBOT_FEATURE)
    if template is None:
        raise ChatbotConfigError('챗봇용 활성 프롬프트가 설정되지 않았습니다.')

    context_block, links = _build_dynamic_context(user_message)
    system_message = {'role': 'system', 'content': f'{template.system_prompt}\n\n{context_block}'}
    trimmed_history = history[-_MAX_HISTORY_TURNS:]
    messages = [system_message, *trimmed_history, {'role': 'user', 'content': user_message}]

    text = SuhAiderClient().chat(model=template.model, messages=messages)
    return ChatReply(text=text, links=links)


def _extract_tokens(user_message: str) -> list[str]:
    tokens = _TOKEN_PATTERN.split(user_message)
    filtered = [token for token in tokens if len(token) >= _MIN_TOKEN_LENGTH]
    return filtered[:_MAX_TOKENS]


def _build_dynamic_context(user_message: str) -> tuple[str, list[ChatLink]]:
    tokens = _extract_tokens(user_message)
    project_text, project_links = _build_project_section(tokens)
    post_text, post_links = _build_post_section(tokens)
    sections = [
        _build_profile_section(),
        _build_career_section(),
        _build_certification_section(),
        _build_activity_section(),
        _build_pull_request_highlight_section(),
        project_text,
        post_text,
        _build_skill_section(tokens),
    ]
    text = '\n\n'.join(filter(None, sections))
    links = _dedupe_links([*project_links, *post_links])
    return text, links


def _dedupe_links(links: list[ChatLink]) -> list[ChatLink]:
    """같은 url을 가리키는 링크가 여러 개면 처음 것만 남긴다.

    외부 링크가 없는 프로젝트가 여러 개 매칭되면 전부 동일한 '프로젝트 목록' 폴백
    URL을 반환하므로, 그대로 두면 Alpine의 :key="link.url"이 충돌하고 화면에
    똑같은 버튼이 여러 개 뜬다.
    """
    seen_urls: set[str] = set()
    deduped: list[ChatLink] = []
    for link in links:
        if link.url in seen_urls:
            continue
        seen_urls.add(link.url)
        deduped.append(link)
    return deduped


def _build_profile_section() -> str:
    profile = Profile.objects.order_by('pk').first()
    if profile is None:
        return ''
    lines = [f'이름: {profile.name}', f'한 줄 소개: {profile.tagline}']
    if profile.bio:
        lines.append(f'소개: {profile.bio}')
    if profile.email:
        lines.append(f'이메일: {profile.email}')
    if profile.github_url:
        lines.append(f'GitHub: {profile.github_url}')
    if profile.linkedin_url:
        lines.append(f'LinkedIn: {profile.linkedin_url}')
    if profile.blog_url:
        lines.append(f'블로그: {profile.blog_url}')
    return '[프로필]\n' + '\n'.join(lines)


def _build_career_section() -> str:
    careers = Career.objects.exclude(category=Career.Category.AWARD)[:_STATIC_SECTION_LIMIT]
    if not careers:
        return ''
    lines = [_format_career_line(career) for career in careers]
    return '[경력]\n' + '\n'.join(lines)


def _format_career_line(career: Career) -> str:
    period_end = career.period_end.strftime('%Y.%m') if career.period_end else '현재'
    period = f"{career.period_start.strftime('%Y.%m')}~{period_end}"
    line = f'- [{career.get_category_display()}] {career.organization} — {career.role} ({period})'
    if career.description:
        line += f'\n  {career.description}'
    return line


def _build_certification_section() -> str:
    certifications = Certification.objects.all()[:_STATIC_SECTION_LIMIT]
    if not certifications:
        return ''
    lines = [
        f"- {certification.name} ({certification.issuer}, {certification.acquired_date.strftime('%Y.%m')} 취득)"
        for certification in certifications
    ]
    return '[자격증]\n' + '\n'.join(lines)


def _build_activity_section() -> str:
    activities = Activity.objects.all()[:_STATIC_SECTION_LIMIT]
    if not activities:
        return ''
    lines = [_format_activity_line(activity) for activity in activities]
    return '[대외활동]\n' + '\n'.join(lines)


def _format_activity_line(activity: Activity) -> str:
    line = f'- {activity.name}'
    if activity.period:
        line += f' ({activity.period})'
    if activity.description:
        line += f'\n  {activity.description}'
    return line


def _build_pull_request_highlight_section() -> str:
    highlights = PullRequestHighlight.objects.all()[:_STATIC_SECTION_LIMIT]
    if not highlights:
        return ''
    lines = [_format_pull_request_highlight_line(highlight) for highlight in highlights]
    return '[대표 PR]\n' + '\n'.join(lines)


def _format_pull_request_highlight_line(highlight: PullRequestHighlight) -> str:
    line = f'- [{highlight.repo_name}] {highlight.title}'
    if highlight.description:
        line += f'\n  {highlight.description}'
    return line


def _build_project_section(tokens: list[str]) -> tuple[str, list[ChatLink]]:
    if not tokens:
        return '', []
    query = reduce(or_, (Q(title__icontains=token) | Q(description__icontains=token) for token in tokens))
    projects = Project.objects.filter(query).order_by(
        '-is_featured', 'category__order', 'order', '-created_at',
    )[:_SEARCH_RESULT_LIMIT]
    if not projects:
        return '', []
    lines = [_format_project_line(project) for project in projects]
    text = '[관련 프로젝트]\n' + '\n'.join(lines)
    links = [_project_recommendation_link(project) for project in projects]
    return text, links


def _format_project_line(project: Project) -> str:
    """프로젝트 한 개를 컨텍스트 텍스트로 만든다. role/highlights가 있으면 이어붙인다."""
    lines = [f'- {project.title}: {project.description}']
    if project.role:
        lines.append(f'  역할: {project.role}')
    if project.highlights:
        lines.append(f'  주요 성과: {", ".join(project.highlights)}')
    return '\n'.join(lines)


def _build_post_section(tokens: list[str]) -> tuple[str, list[ChatLink]]:
    if not tokens:
        return '', []
    query = reduce(
        or_,
        (
            Q(title__icontains=token) | Q(summary__icontains=token) | Q(tags__name__icontains=token)
            for token in tokens
        ),
    )
    posts = Post.objects.filter(is_published=True).filter(query).distinct()[:_SEARCH_RESULT_LIMIT]
    if not posts:
        return '', []
    lines = [f'- {post.title}: {post.summary}' for post in posts]
    text = '[관련 블로그 글]\n' + '\n'.join(lines)
    links = [
        ChatLink(label=f'{post.title} →', url=reverse('site:blog-detail', kwargs={'slug': post.slug}))
        for post in posts
    ]
    return text, links


def _build_skill_section(tokens: list[str]) -> str:
    if not tokens:
        return ''
    query = reduce(or_, (Q(name__icontains=token) for token in tokens))
    skills = Skill.objects.filter(query)[:_SEARCH_RESULT_LIMIT]
    if not skills:
        return ''
    names = ', '.join(skill.name for skill in skills)
    return f'[관련 기술스택]\n{names}'
