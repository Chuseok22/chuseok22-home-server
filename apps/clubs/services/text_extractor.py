import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)'}
_MAX_TEXT_CHARS = 8000
_MIN_TEXT_CHARS = 200


def fetch_page_text(url: str) -> str | None:
    """URL의 본문을 CSS 구조에 의존하지 않고 텍스트로 추출한다.

    <script>/<style>/<noscript> 등 비본문 태그를 제거한 뒤 전체 텍스트를 반환한다 — 특정
    클래스명·레이아웃에 의존하지 않아 사이트 리뉴얼에도 코드 수정 없이 버틴다. 추출된 텍스트가
    비정상적으로 짧으면(_MIN_TEXT_CHARS 미만) JS 렌더링이 필요한 SPA 셸만 받았을 가능성이 있어
    None을 반환한다 — 호출자는 이를 실패로 처리해야 한다.
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error('페이지 요청 실패 (%s): %s', url, e)
        return None

    soup = BeautifulSoup(response.text, 'lxml')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    text = re.sub(r'\s+', ' ', soup.get_text(separator=' ', strip=True)).strip()
    if len(text) < _MIN_TEXT_CHARS:
        logger.warning(
            '페이지 본문이 비정상적으로 짧음 (%s자, url=%s) — JS 렌더링이 필요한 페이지일 수 있음',
            len(text), url,
        )
        return None

    return text[:_MAX_TEXT_CHARS]


def extract_page_links(url: str) -> list[str]:
    """URL의 <a href> 절대 링크 목록을 추출한다.

    LLM이 응답한 apply_url이 실제로 원문 페이지에 존재하는 링크인지 grounding하기 위해 쓰인다
    (evidence_quote의 텍스트 grounding과 같은 원리를 링크에도 적용). 요청 실패 시 빈 리스트를
    반환한다 — 링크 grounding은 apply_url 검증을 강화하는 부가 안전장치일 뿐 감시 자체의 성공
    조건이 아니므로, 실패로 카운트하지 않는다(호출자는 빈 리스트를 "grounding 근거 없음"으로
    취급해 길이·스킴 검사만으로 완화해야 한다).
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning('링크 추출용 페이지 요청 실패 (%s): %s', url, e)
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    links = []
    for a in soup.find_all('a', href=True):
        absolute = urljoin(url, a['href'])
        if absolute.startswith(('http://', 'https://')):
            links.append(absolute)
    return links
