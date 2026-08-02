from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.ai.services.prompt_template import CHATBOT_FEATURE
from apps.ai.models import PromptTemplate
from apps.blog.models import Category, Post, Tag
from apps.profile.models import Profile, Skill
from apps.projects.models import Project, ProjectCategory, ProjectStatus
from apps.site.services.chatbot import (
    ChatbotConfigError,
    ChatLink,
    _MAX_TOKENS,
    _extract_tokens,
    _project_recommendation_link,
    get_chat_reply,
)


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

    assert reply.text == '안녕하세요!'
    assert reply.links == []
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
def test_프로필_연락처_정보가_있으면_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    Profile.objects.create(
        name='백지훈', tagline='백엔드 개발자',
        email='bjh59629@gmail.com', github_url='https://github.com/Chuseok22',
        linkedin_url='https://linkedin.com/in/chuseok22', blog_url='https://chuseok22.com',
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('연락처 알려줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '이메일: bjh59629@gmail.com' in system_content
    assert 'GitHub: https://github.com/Chuseok22' in system_content
    assert 'LinkedIn: https://linkedin.com/in/chuseok22' in system_content
    assert '블로그: https://chuseok22.com' in system_content


@pytest.mark.django_db
def test_프로필_연락처_정보가_비어있으면_컨텍스트에서_생략된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('연락처 알려줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '이메일:' not in system_content
    assert 'GitHub:' not in system_content
    assert 'LinkedIn:' not in system_content
    assert '블로그:' not in system_content


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


@pytest.mark.django_db
def test_title_href가_있으면_우선_사용한다() -> None:
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    project = Project.objects.create(
        category=category, title='Version Management', description='설명', status=status,
        title_href='https://title.example.com', web_site_href='https://site.example.com',
        github_href='https://github.com/example/repo',
    )

    link = _project_recommendation_link(project)

    assert link == ChatLink(label='Version Management ↗', url='https://title.example.com')


@pytest.mark.django_db
def test_title_href가_없으면_web_site_href를_사용한다() -> None:
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    project = Project.objects.create(
        category=category, title='Version Management', description='설명', status=status,
        web_site_href='https://site.example.com', github_href='https://github.com/example/repo',
    )

    link = _project_recommendation_link(project)

    assert link == ChatLink(label='Version Management ↗', url='https://site.example.com')


@pytest.mark.django_db
def test_title_href와_web_site_href가_없으면_github_href를_사용한다() -> None:
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    project = Project.objects.create(
        category=category, title='Version Management', description='설명', status=status,
        github_href='https://github.com/example/repo',
    )

    link = _project_recommendation_link(project)

    assert link == ChatLink(label='Version Management ↗', url='https://github.com/example/repo')


@pytest.mark.django_db
def test_외부_링크가_전부_없으면_프로젝트_목록으로_폴백한다() -> None:
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    project = Project.objects.create(
        category=category, title='Version Management', description='설명', status=status,
    )

    link = _project_recommendation_link(project)

    assert link == ChatLink(label='프로젝트 목록 →', url=reverse('site:projects'))


@pytest.mark.django_db
def test_관련_프로젝트가_있으면_links에_대표_링크가_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    Project.objects.create(
        category=category, title='홈서버 프로젝트', description='Django 기반 홈서버',
        status=status, title_href='https://external.example.com/homeserver',
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        reply = get_chat_reply('홈서버 프로젝트에 대해 알려줘', [])

    assert reply.links == [
        ChatLink(label='홈서버 프로젝트 ↗', url='https://external.example.com/homeserver'),
    ]


@pytest.mark.django_db
def test_관련_블로그_글이_있으면_links에_상세_페이지_링크가_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = Category.objects.create(name='개발')
    Post.objects.create(
        title='배포 자동화 회고', slug='deploy-post', summary='배포 과정 정리',
        content='내용', category=category, is_published=True,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        reply = get_chat_reply('배포 자동화 회고 보여줘', [])

    assert reply.links == [
        ChatLink(label='배포 자동화 회고 →', url=reverse('site:blog-detail', kwargs={'slug': 'deploy-post'})),
    ]


@pytest.mark.django_db
def test_프로젝트_링크가_블로그_링크보다_먼저_온다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    Project.objects.create(
        category=category, title='홈서버', description='홈서버 배포 자동화 프로젝트',
        status=status, title_href='https://external.example.com/homeserver',
    )
    blog_category = Category.objects.create(name='개발')
    Post.objects.create(
        title='홈서버 배포 회고', slug='homeserver-deploy', summary='배포 과정 정리',
        content='내용', category=blog_category, is_published=True,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        reply = get_chat_reply('홈서버 배포에 대해 알려줘', [])

    assert reply.links == [
        ChatLink(label='홈서버 ↗', url='https://external.example.com/homeserver'),
        ChatLink(label='홈서버 배포 회고 →', url=reverse('site:blog-detail', kwargs={'slug': 'homeserver-deploy'})),
    ]


@pytest.mark.django_db
def test_외부_링크_없는_프로젝트가_여러_개면_목록_링크는_하나만_남는다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    Project.objects.create(category=category, title='홈서버 프로젝트A', description='설명', status=status)
    Project.objects.create(category=category, title='홈서버 프로젝트B', description='설명', status=status)

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        reply = get_chat_reply('홈서버 프로젝트 알려줘', [])

    assert reply.links == [ChatLink(label='프로젝트 목록 →', url=reverse('site:projects'))]


@pytest.mark.django_db
def test_매칭되는_항목이_없으면_links는_빈_리스트다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        reply = get_chat_reply('안녕하세요', [])

    assert reply.links == []


@pytest.mark.django_db
def test_대표작_프로젝트가_비대표작보다_먼저_정렬된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    # order 값을 다르게 둬서 결과가 created_at 타이밍에 의존하지 않도록 한다. is_featured
    # 정렬이 없으면 Meta.ordering(order 오름차순)에 따라 order=0인 비대표작이 먼저 나와
    # 확정적으로 RED가 되고, is_featured 정렬이 적용되면 order보다 -is_featured가 먼저
    # 적용되어 order=1인 대표작이 먼저 나와 확정적으로 GREEN이 된다.
    Project.objects.create(
        category=category, title='순서상 앞선 비대표작 홈서버 프로젝트', description='설명',
        status=status, order=0, is_featured=False,
    )
    Project.objects.create(
        category=category, title='순서상 뒤인 대표작 홈서버 프로젝트', description='설명',
        status=status, order=1, is_featured=True,
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('홈서버 프로젝트에 대해 알려줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert system_content.index('순서상 뒤인 대표작 홈서버 프로젝트') < system_content.index('순서상 앞선 비대표작 홈서버 프로젝트')


@pytest.mark.django_db
def test_role과_highlights가_있으면_컨텍스트에_포함된다() -> None:
    PromptTemplate.objects.create(
        feature=CHATBOT_FEATURE, name='기본', system_prompt='시스템',
        model='functiongemma', is_active=True,
    )
    category = ProjectCategory.objects.create(name='개인 프로젝트')
    status = ProjectStatus.objects.get(name='완료')
    Project.objects.create(
        category=category, title='홈서버 프로젝트', description='설명', status=status,
        role='백엔드 설계 및 배포 자동화',
        highlights=['CI/CD 파이프라인 구축', '월 방문자 1만 달성'],
    )

    with patch('apps.site.services.chatbot.SuhAiderClient') as mock_client_cls:
        mock_client_cls.return_value.chat.return_value = '응답'
        get_chat_reply('홈서버 프로젝트에 대해 알려줘', [])

    system_content = mock_client_cls.return_value.chat.call_args.kwargs['messages'][0]['content']
    assert '역할: 백엔드 설계 및 배포 자동화' in system_content
    assert '주요 성과: CI/CD 파이프라인 구축, 월 방문자 1만 달성' in system_content
