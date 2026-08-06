(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function pickImageWidthPercent(anchorElement) {
    return new Promise((resolve) => {
      const popup = document.createElement('div');
      popup.className = 'blog-image-size-popup';

      const options = [
        { label: '원본', percent: 100 },
        { label: '중간(60%)', percent: 60 },
        { label: '작게(30%)', percent: 30 },
      ];

      function cleanup(result) {
        popup.remove();
        document.removeEventListener('keydown', onKeyDown);
        document.removeEventListener('mousedown', onOutsideClick);
        resolve(result);
      }

      function onKeyDown(event) {
        if (event.key === 'Escape') {
          cleanup(null);
        }
      }

      function onOutsideClick(event) {
        if (!popup.contains(event.target)) {
          cleanup(null);
        }
      }

      options.forEach(({ label, percent }) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label;
        button.addEventListener('click', () => cleanup(percent));
        popup.appendChild(button);
      });

      const cancelButton = document.createElement('button');
      cancelButton.type = 'button';
      cancelButton.textContent = '취소';
      cancelButton.addEventListener('click', () => cleanup(null));
      popup.appendChild(cancelButton);

      const rect = anchorElement.getBoundingClientRect();
      popup.style.position = 'fixed';
      popup.style.top = `${rect.top + 8}px`;
      popup.style.left = `${rect.left + 8}px`;

      document.body.appendChild(popup);
      document.addEventListener('keydown', onKeyDown);
      // 팝업을 띄운 클릭 자체가 곧바로 outside-click으로 잡히지 않도록 다음 tick에 등록한다.
      setTimeout(() => document.addEventListener('mousedown', onOutsideClick), 0);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('id_content');
    if (!textarea) {
      return;
    }

    if (typeof EasyMDE === 'undefined') {
      console.warn('EasyMDE 로드에 실패했습니다. CDN 연결 상태를 확인하세요.');
      return;
    }

    // 현재 페이지가 .../<id>/change/ 또는 .../add/ 이므로, 같은 ModelAdmin 하위의
    // 형제 경로로 업로드·미리보기 엔드포인트를 계산한다. id를 남겨두면 Django admin의
    // 레거시 경로(<path:object_id>/)에 잘못 매칭되어 리다이렉트가 발생하므로 함께 제거한다.
    const uploadUrl = window.location.pathname.replace(/\/(?:\d+\/change|add)\/?$/, '/upload-media/');
    const previewUrl = window.location.pathname.replace(/\/(?:\d+\/change|add)\/?$/, '/preview/');

    let previewDebounceTimer = null;
    let latestPreviewToken = 0;

    function schedulePreviewFetch(plainText, previewEl, requestToken) {
      fetch(previewUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `content=${encodeURIComponent(plainText)}`,
      })
        .then((response) => response.json())
        .then((data) => {
          if (requestToken !== latestPreviewToken || data.html === undefined) {
            return;
          }
          previewEl.innerHTML = data.html;
        })
        .catch(() => {
          // 실패 시 마지막으로 성공한 렌더링을 그대로 유지하고, 다음 입력에서 재시도한다.
        });
    }

    let easyMDE;

    easyMDE = new EasyMDE({
      element: textarea,
      autofocus: true,
      spellChecker: false,
      sideBySideFullscreen: false,
      toolbar: ['upload-image', '|', 'side-by-side'],
      uploadImage: true,
      imageAccept: '*/*', // 기본값(png/jpeg/gif/avif)은 webp·mp4·pdf 선택을 막으므로 전체 허용으로 넓힌다
      imageUploadFunction: function (file, onSuccess, onError) {
        const isImage = file.type.startsWith('image/');

        function performUpload(widthPercent) {
          const formData = new FormData();
          formData.append('file', file);

          fetch(uploadUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (!data.success) {
                onError(data.error_message || '업로드에 실패했습니다.');
                return;
              }

              // EasyMDE의 imageUploadFunction 계약상 onSuccess는 반드시 실제 URL 문자열로
              // 호출해야 한다 — 내부적으로 고정 템플릿(예: uploadedImage: ["![](#url#)", ""])의
              // #url# 자리에 넣어 커서 위치에 자동 삽입하기 때문에, 여기에 마크다운/HTML
              // 문자열을 넘기면 그 문자열이 통째로 #url# 자리에 끼워져 이중 래핑되거나
              // 깨진다(EasyMDE 2.21.0 실제 번들 코드로 확인됨). 그래서 onSuccess(data.url)로
              // EasyMDE가 스스로 삽입을 완료(상태바 갱신 포함)하게 한 뒤, 방금 삽입된
              // 커서 범위를 우리가 원하는 최종 스니펫으로 즉시 덮어쓴다. 이미지(원본/크기조절)·
              // 동영상·문서 모두 이 하나의 경로로 처리된다.
              const from = easyMDE.codemirror.getCursor('from');
              onSuccess(data.url);
              const to = easyMDE.codemirror.getCursor();

              const snippet = (isImage && widthPercent !== null && widthPercent !== 100)
                ? `<img src="${data.url}" alt="업로드 이미지" width="${widthPercent}%">`
                : data.markdown;
              easyMDE.codemirror.replaceRange(snippet, from, to);
            })
            .catch(() => onError('업로드 중 오류가 발생했습니다.'));
        }

        if (!isImage) {
          performUpload(null);
          return;
        }

        pickImageWidthPercent(easyMDE.codemirror.getWrapperElement()).then((widthPercent) => {
          if (widthPercent === null) {
            return; // 취소 시 조용히 아무 것도 하지 않는다 — 파일 선택이 없었던 것과 동일하게 처리
          }
          performUpload(widthPercent);
        });
      },
      previewRender: function (plainText, previewEl) {
        if (previewDebounceTimer) {
          clearTimeout(previewDebounceTimer);
        }
        const requestToken = ++latestPreviewToken;
        previewDebounceTimer = setTimeout(
          () => schedulePreviewFetch(plainText, previewEl, requestToken),
          300,
        );
        // 실제 HTML을 그대로 반환하면 EasyMDE가 매 키 입력마다 동일한 innerHTML을
        // 재할당해 미리보기 DOM을 통째로 리렌더링한다(이미지·동영상 노드 재생성 포함).
        // 실제 갱신은 위 디바운스된 fetch 콜백에서 처리하므로 여기서는 null을 반환해
        // EasyMDE가 innerHTML을 건드리지 않게 한다(느슨한 비교 대상이라 undefined가
        // 아닌 명시적 null이어야 한다).
        return null;
      },
    });

    easyMDE.toggleSideBySide();
  });
})();
