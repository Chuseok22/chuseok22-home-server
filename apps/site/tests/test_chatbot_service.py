from unittest.mock import patch

import pytest

from apps.ai.services.prompt_template import CHATBOT_FEATURE
from apps.ai.models import PromptTemplate
from apps.blog.models import Category, Post, Tag
from apps.profile.models import Profile, Skill
from apps.projects.models import Project, ProjectCategory, ProjectStatus
from apps.site.services.chatbot import ChatbotConfigError, _MAX_TOKENS, _extract_tokens, get_chat_reply


@pytest.mark.django_db
def test_활성_프롬프트가_없으면_ChatbotConfigError를_raise한다() -> None:
    with pytest.raises(ChatbotConfigError):
        get_chat_reply('안녕', [])


@pytest.mark.django_db
def test_정상_흐름에서_SuhAiderClient_chat이_시스템_프롬프트와_함께_호출된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE,
        name='기본',
        system_prompt='당신은 백지훈의 AI 비서입니다.',
        model='functiongemma',
        is_active=True,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '안녕하세요!'
        reply = get_chat_reply('안녕', [])

    assert reply == '안녕하세요!'
    mock_client_cls.return_value.chat.assert_called_once()
    call_kwargs = mock_client_cls.return_value.chat.call_args.kwargs
    assert call_kwargs['model'] == 'functiongemma'
    assert call_kwargs['messages'][0]['role'] == 'system'
    assert '당신은 백지훈의 AI 비서입니다.' in call_kwargs['messages'][0]['content']
    assert call_kwargs['messages'][-1] == {'role': 'user', 'content': '안녕'}


@pytest.mark.django_db
def test_프로필_정보는_항상_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    Profile.objects.create(name='백지훈', tagline='백엔드 개발자', bio='Django를 좋아합니다.')

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('안녕', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '백지훈' in system_content
    assert '백엔드 개발자' in system_content


@pytest.mark.django_db
def test_메시지_토큰과_일치하는_프로젝트가_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    # ProjectStatus.name은 unique 제약이며 '완료'는 시딩 마이그레이션(0004)에서 이미 생성되어
    # 있으므로(apps/projects/tests/test_models.py와 동일 관례) 새로 만들지 않고 조회해서 사용한다.
    status = ProjectStatus.objects.get(name='완료')
    Project.objects.create(
        category=category, title='홈서버 프로젝트', description='Django 기반 홈서버',
        status=status,
    )
    Project.objects.create(
        category=category, title='무관한 프로젝트', description='관련 없는 설명',
        status=status,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('홈서버 프로젝트에 대해 알려줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '홈서버 프로젝트' in system_content
    assert '무관한 프로젝트' not in system_content


@pytest.mark.django_db
def test_비공개_블로그_글은_토큰이_일치해도_컨텍스트에서_제외된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = Category.objects.create(name='개발')
    Post.objects.create(
        title='비공개 글', slug='private-post', summary='비공개 요약', content='내용',
        category=category, is_published=False,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('비공개 글 찾아줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '비공개 글' not in system_content


@pytest.mark.django_db
def test_공개_블로그_글은_태그_토큰_일치로도_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = Category.objects.create(name='개발')
    tag = Tag.objects.create(name='Kubernetes')
    post = Post.objects.create(
        title='배포 자동화 회고', slug='deploy-post', summary='배포 과정 정리',
        content='내용', category=category, is_published=True,
    )
    post.tags.add(tag)

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('Kubernetes 써본 적 있어?', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '배포 자동화 회고' in system_content


@pytest.mark.django_db
def test_기술스택_검색어와_일치하면_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django')
    Skill.objects.create(category=Skill.Category.FRONTEND, name='React')

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('Django 써봤어?', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert 'Django' in system_content
    assert 'React' not in system_content


def test_토큰이_20개를_초과하면_20개로_제한된다() -> None:
    # 유효 토큰(길이 2 이상) 30개를 만들어 최대 개수(_MAX_TOKENS) 초과 시 잘리는지 확인한다.
    message = ' '.join(f'단어{i}' for i in range(30))

    tokens = _extract_tokens(message)

    assert len(tokens) == _MAX_TOKENS
    assert tokens == [f'단어{i}' for i in range(_MAX_TOKENS)]


@pytest.mark.django_db
def test_history는_최근_10턴만_사용한다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    history = [{'role': 'user', 'content': f'메시지{i}'} for i in range(15)]

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('안녕', history)

    messages = mock_client_cls.return_value.chat.call_args.kwargs['messages']
    # messages = [system, *trimmed_history(10), user] → 총 12개
    assert len(messages) == 12
    assert messages[1] == {'role': 'user', 'content': '메시지5'}
