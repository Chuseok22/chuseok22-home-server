import re
from functools import reduce
from operator import or_

from django.db.models import Q

from apps.ai.services.prompt_template import CHATBOT_FEATURE, get_active_prompt
from apps.ai.services.suh_aider_client import SuhAiderClient
from apps.blog.models import Post
from apps.profile.models import Profile, Skill
from apps.projects.models import Project

_MAX_HISTORY_TURNS = 10
_SEARCH_RESULT_LIMIT = 3
_MIN_TOKEN_LENGTH = 2
# 공백/구두점 기준으로만 나누는 러프한 토큰화 — 한국어 조사가 붙은 형태("프로젝트에")는 그대로
# 하나의 토큰이 되므로 완벽하지 않지만, 형태소 분석 없이 "관련 있을 법한 항목을 놓치지 않는" 목적에는
# 충분하다고 판단했다(스펙의 "간단한 검색" 합의 사항).
_TOKEN_PATTERN = re.compile(r'[^\w가-힣]+')


class ChatbotConfigError(Exception):
    """챗봇용 활성 프롬프트가 설정되지 않았을 때 발생한다."""


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
    return [token for token in tokens if len(token) >= _MIN_TOKEN_LENGTH]


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
    profile = Profile.objects.first()
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
