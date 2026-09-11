import logging
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 강의 영상은 재생시간이 길 수 있어 ffmpeg remux 타임아웃을 넉넉히(2시간) 둔다.
_FFMPEG_TIMEOUT_SECONDS = 7200
_STDERR_LOG_MAX_LENGTH = 500
# CDN이 Referer 헤더를 검사해 403을 반환할 가능성에 대비한 폴백 옵션값.
_REFERER_HEADER_VALUE = 'Referer: https://ecampus.sejong.ac.kr/\r\n'
_URL_RE = re.compile(r'https?://[^\s\'"]+')


class HlsDownloader:
    """HLS(m3u8) 스트림을 ffmpeg로 mp4 파일에 remux(무재인코딩 병합)하는 서비스.

    `ffmpeg -i <m3u8_url> -c copy <output>` 한 줄로 세그먼트를 순서대로 받아 병합한다
    (대상 CDN이 단일 화질/암호화 없는 표준 HLS VOD 재생목록임을 실측으로 확인 완료).
    """

    def download_to_mp4(self, m3u8_url: str, output_path: Path) -> None:
        """m3u8_url의 HLS 스트림을 output_path에 mp4로 저장한다.

        완료 전까지는 임시 파일명(`<output_path>.part`)에 쓰고 성공 시에만 최종
        파일명으로 rename한다 — 다운로드 중 서버가 재시작(SIGKILL)돼도 미완성 부분
        파일이 완성본처럼 남지 않도록 하기 위함이다.

        CDN이 Referer 헤더를 검사해 403을 반환하는 경우에 대비해, 1차 시도가 403으로
        실패하면 Referer 헤더를 추가해 1회만 재시도한다.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_name(output_path.name + '.part')

        try:
            try:
                self._run_ffmpeg(m3u8_url, temp_path, with_referer=False)
            except subprocess.CalledProcessError as e:
                stderr_text = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
                if '403' not in stderr_text:
                    raise
                logger.warning('ffmpeg 다운로드가 403으로 실패해 Referer 헤더를 추가해 재시도합니다.')
                self._run_ffmpeg(m3u8_url, temp_path, with_referer=True)
        except Exception:
            # 재시도까지 최종 실패하면 미완성 임시 파일을 남기지 않는다. 삭제는 부수
            # 효과일 뿐이므로 실패 자체는 그대로 재전파한다.
            temp_path.unlink(missing_ok=True)
            raise

        temp_path.rename(output_path)

    def _run_ffmpeg(self, m3u8_url: str, temp_path: Path, with_referer: bool) -> None:
        command = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error']
        if with_referer:
            command += ['-headers', _REFERER_HEADER_VALUE]
        # 출력 파일이 임시로 `.mp4.part`로 끝나 ffmpeg가 확장자로 컨테이너 포맷을 추론하지
        # 못한다("Unable to find a suitable output format") — `-f mp4`로 명시해 우회한다.
        command += ['-i', m3u8_url, '-c', 'copy', '-f', 'mp4', str(temp_path)]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=_FFMPEG_TIMEOUT_SECONDS,
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
            masked_stderr = _mask_urls_in_text(stderr_text)[:_STDERR_LOG_MAX_LENGTH]
            logger.error('ffmpeg 다운로드 실패: %s', masked_stderr)
            raise


def _mask_token_in_url(url: str) -> str:
    """URL의 scheme+host만 남기고 경로/쿼리를 마스킹한다.

    m3u8/세그먼트 URL은 인증 토큰이 쿼리 파라미터가 아니라 경로 세그먼트에 포함될 수
    있어(Naver Cloud CDN), 특정 파라미터명만 마스킹하는 방식(sejong_auth.py의
    `_mask_token_in_url`)이 아니라 경로/쿼리 전체를 마스킹하는 방식을 쓴다.
    """
    parsed = urlparse(url)
    return f'{parsed.scheme}://{parsed.netloc}/***'


def _mask_urls_in_text(text: str) -> str:
    """텍스트에 포함된 모든 URL을 마스킹한다.

    ffmpeg stderr는 m3u8 URL뿐 아니라 실패한 세그먼트 URL도 그대로 출력하므로,
    로깅 전 텍스트 전체에서 URL 패턴을 찾아 일괄 마스킹한다.
    """
    return _URL_RE.sub(lambda match: _mask_token_in_url(match.group(0)), text)
