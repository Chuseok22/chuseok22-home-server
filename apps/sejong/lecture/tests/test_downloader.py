import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from apps.sejong.lecture.services.downloader import HlsDownloader, _mask_token_in_url, _mask_urls_in_text


def _fake_run_creates_temp_file(temp_path: Path) -> MagicMock:
    """subprocess.run을 대신할 MagicMock. 실제 ffmpeg처럼 temp 파일을 생성해둔다."""

    def _side_effect(*_args: object, **_kwargs: object) -> MagicMock:
        temp_path.write_bytes(b'fake mp4 bytes')
        return MagicMock(returncode=0)

    return MagicMock(side_effect=_side_effect)


def test_download_to_mp4_success_renames_temp_file_to_output(tmp_path: Path) -> None:
    output_path = tmp_path / 'nested' / 'lecture.mp4'
    temp_path = output_path.with_name(output_path.name + '.part')

    with patch('apps.sejong.lecture.services.downloader.subprocess.run', _fake_run_creates_temp_file(temp_path)) as mock_run:
        HlsDownloader().download_to_mp4('https://cdn.example.com/token123/index.m3u8', output_path)

    assert mock_run.call_count == 1
    assert output_path.exists()
    assert not temp_path.exists()
    assert output_path.read_bytes() == b'fake mp4 bytes'

    command = mock_run.call_args.args[0]
    assert command[0] == 'ffmpeg'
    assert '-headers' not in command
    assert command[-1] == str(temp_path)
    # temp_path가 `.mp4.part`로 끝나 확장자로 컨테이너 포맷을 추론할 수 없으므로
    # `-f mp4`를 명시해야 한다(누락 시 ffmpeg가 "Unable to find a suitable output format").
    assert command[command.index('-f') + 1] == 'mp4'


def test_download_to_mp4_reraises_on_non_403_failure_without_retry(tmp_path: Path) -> None:
    output_path = tmp_path / 'lecture.mp4'
    error = subprocess.CalledProcessError(returncode=1, cmd=['ffmpeg'], stderr=b'Connection refused')

    with patch('apps.sejong.lecture.services.downloader.subprocess.run', side_effect=error) as mock_run:
        try:
            HlsDownloader().download_to_mp4('https://cdn.example.com/token123/index.m3u8', output_path)
            raise AssertionError('CalledProcessError가 재전파되어야 한다')
        except subprocess.CalledProcessError:
            pass

    assert mock_run.call_count == 1
    assert not output_path.exists()


def test_download_to_mp4_retries_with_referer_header_on_403(tmp_path: Path) -> None:
    output_path = tmp_path / 'lecture.mp4'
    temp_path = output_path.with_name(output_path.name + '.part')
    forbidden_error = subprocess.CalledProcessError(returncode=1, cmd=['ffmpeg'], stderr=b'HTTP error 403 Forbidden')

    calls: list[list[str]] = []

    def _side_effect(command: list[str], **_kwargs: object) -> MagicMock:
        calls.append(command)
        if len(calls) == 1:
            raise forbidden_error
        temp_path.write_bytes(b'fake mp4 bytes')
        return MagicMock(returncode=0)

    with patch('apps.sejong.lecture.services.downloader.subprocess.run', side_effect=_side_effect):
        HlsDownloader().download_to_mp4('https://cdn.example.com/token123/index.m3u8', output_path)

    assert len(calls) == 2
    assert '-headers' not in calls[0]
    assert '-headers' in calls[1]
    assert output_path.exists()


def test_mask_token_in_url_strips_path_and_query() -> None:
    masked = _mask_token_in_url('https://cdn.example.com/secret-token-abc/index.m3u8?auth=xyz')

    assert masked == 'https://cdn.example.com/***'
    assert 'secret-token-abc' not in masked
    assert 'xyz' not in masked


def test_mask_urls_in_text_masks_every_url_occurrence() -> None:
    text = (
        "Failed to open segment 'https://cdn.example.com/token123/segment-1-v1-a1.ts': "
        "server returned 403 Forbidden for url https://cdn.example.com/token123/index.m3u8"
    )

    masked = _mask_urls_in_text(text)

    assert 'token123' not in masked
    assert masked.count('https://cdn.example.com/***') == 2
