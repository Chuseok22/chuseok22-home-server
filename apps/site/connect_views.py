from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from apps.site.models import ConnectLink, ConnectProfile
from apps.site.services.vcard import build_vcard

_DEFAULT_VCARD_FILENAME = 'contact'


def _get_connect_profile() -> ConnectProfile:
    profile = ConnectProfile.objects.first()
    if profile is None:
        # 배포 직후 Admin 입력 전에는 헤더를 그릴 수 없으므로 빈 페이지 대신 404로 응답한다.
        raise Http404('Connect 프로필이 아직 등록되지 않았습니다.')
    return profile


@require_http_methods(['GET', 'HEAD'])
def connect(request: HttpRequest) -> HttpResponse:
    profile = _get_connect_profile()
    links = ConnectLink.objects.filter(is_active=True)
    # 공유 미리보기 크롤러는 상대 경로를 해석하지 못하므로 명함 이미지는 절대 URL로 넘긴다.
    share_image_url = request.build_absolute_uri(profile.business_card.url) if profile.business_card else ''
    return render(
        request,
        'site/connect.html',
        {'profile': profile, 'links': links, 'share_image_url': share_image_url},
    )


@require_http_methods(['GET', 'HEAD'])
def connect_vcard(request: HttpRequest) -> HttpResponse:
    profile = _get_connect_profile()
    # 한글 등 비ASCII 이름은 slugify 결과가 비므로 기본 파일명으로 대체한다.
    filename = slugify(profile.english_name) or _DEFAULT_VCARD_FILENAME
    response = HttpResponse(
        build_vcard(profile, request.build_absolute_uri('/')),
        content_type='text/vcard; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.vcf"'
    # 전화번호가 담긴 파일이 검색 결과에 색인되지 않게 한다.
    response['X-Robots-Tag'] = 'noindex'
    return response
