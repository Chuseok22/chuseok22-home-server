import re
from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.db.models import Q
from django.urls import reverse

from apps.ai.services.prompt_template import CHATBOT_FEATURE, get_active_prompt
from apps.ai.services.suh_aider_client import SuhAiderClient
from apps.blog.models import Post
from apps.profile.models import Profile, Skill
from apps.projects.models import Project

_MAX_HISTORY_TURNS = 10
_SEARCH_RESULT_LIMIT = 3
_MIN_TOKEN_LENGTH = 2
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


def get_chat_reply(user_message: str, history: list[dict[str, str]]) -> str:
    """활성 프롬프트 + 동적 컨텍스트(프로필/프로젝트/블로그/기술스택)를 조합해 SUH-AIder 응답을 반환한다."""
    template = get_active_prompt(CHATBOT_FEATURE)
    if template is None:
        raise ChatbotConfigError('챗봇용 활성 프롬프트가 설정되지 않았습니다.')

    context_block = _build_dynamic_context(user_message)
    system_message = {'role': 'system', 'content': f'{template.system_prompt}\n\n{context_block}'}
    trimmed_history = history[-_MAX_HISTORY_TURNS:]
    messages = [system_message, *trimmed_history, {'role': 'user', 'content': user_message}]

    return SuhAiderClient().chat(model=template.model, messages=messages)


def _extract_tokens(user_message: str) -> list[str]:
    tokens = _TOKEN_PATTERN.split(user_message)
    filtered = [token for token in tokens if len(token) >= _MIN_TOKEN_LENGTH]
    return filtered[:_MAX_TOKENS]


def _build_dynamic_context(user_message: str) -> str:
    tokens = _extract_tokens(user_message)
    sections = [_build_profile_section()]
    sections += filter(None, [
        _build_project_section(tokens),
        _build_post_section(tokens),
        _build_skill_section(tokens),
    ])
    return '\n\n'.join(filter(None, sections))


def _build_profile_section() -> str:
    profile = Profile.objects.order_by('pk').first()
    if profile is None:
        return ''
    lines = [f'이름: {profile.name}', f'한 줄 소개: {profile.tagline}']
    if profile.bio:
        lines.append(f'소개: {profile.bio}')
    return '[프로필]\n' + '\n'.join(lines)


def _build_project_section(tokens: list[str]) -> str:
    if not tokens:
        return ''
    query = reduce(or_, (Q(title__icontains=token) | Q(description__icontains=token) for token in tokens))
    projects = Project.objects.filter(query)[:_SEARCH_RESULT_LIMIT]
    if not projects:
        return ''
    lines = [f'- {project.title}: {project.description}' for project in projects]
    return '[관련 프로젝트]\n' + '\n'.join(lines)


def _build_post_section(tokens: list[str]) -> str:
    if not tokens:
        return ''
    query = reduce(
        or_,
        (
            Q(title__icontains=token) | Q(summary__icontains=token) | Q(tags__name__icontains=token)
            for token in tokens
        ),
    )
    posts = Post.objects.filter(is_published=True).filter(query).distinct()[:_SEARCH_RESULT_LIMIT]
    if not posts:
        return ''
    lines = [f'- {post.title}: {post.summary}' for post in posts]
    return '[관련 블로그 글]\n' + '\n'.join(lines)


def _build_skill_section(tokens: list[str]) -> str:
    if not tokens:
        return ''
    query = reduce(or_, (Q(name__icontains=token) for token in tokens))
    skills = Skill.objects.filter(query)[:_SEARCH_RESULT_LIMIT]
    if not skills:
        return ''
    names = ', '.join(skill.name for skill in skills)
    return f'[관련 기술스택]\n{names}'
