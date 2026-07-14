(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function debounce(fn, delayMs) {
    let timerId = null;
    return function (...args) {
      if (timerId) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => fn(...args), delayMs);
    };
  }

  document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('id_content');
    if (!textarea) {
      return;
    }

    // post_media_upload.js와 동일한 방식으로 preview/ 엔드포인트 경로를 계산한다.
    const previewUrl = window.location.pathname.replace(/\/(?:\d+\/change|add)\/?$/, '/preview/');

    const originalParent = textarea.parentElement;
    // post_media_upload.js가 textarea 앞에 삽입한 업로드 버튼·파일 입력을 포함해,
    // 이 wrapper 안의 기존 자식들을 모두 그대로 순서 유지한 채 editorPane 안으로 옮긴다.
    // 그렇지 않으면 버튼이 container 바깥(위쪽)에 남아 편집 영역과 분리되어 보인다.
    const existingChildren = Array.from(originalParent.childNodes);

    const container = document.createElement('div');
    container.className = 'blog-split-pane';

    const editorPane = document.createElement('div');
    editorPane.className = 'blog-editor-pane';

    const previewPane = document.createElement('div');
    previewPane.className = 'blog-preview-pane';

    const previewSpinner = document.createElement('span');
    previewSpinner.className = 'admin-loading-spinner blog-preview-spinner';

    originalParent.appendChild(container);
    container.appendChild(editorPane);
    container.appendChild(previewPane);
    container.appendChild(previewSpinner);
    existingChildren.forEach((node) => editorPane.appendChild(node));

    // 응답이 300ms debounce 간격보다 늦게 오면 여러 요청이 동시에 진행될 수 있다.
    // 매 요청에 토큰을 붙여, 가장 최근에 시작한 요청의 결과만 반영하고 스피너도
    // 그 요청이 끝났을 때만 숨긴다. 그렇지 않으면 먼저 끝난 이전 요청이 아직
    // 진행 중인 최신 요청의 스피너를 꺼버릴 수 있다.
    let latestRequestToken = 0;

    function renderPreview() {
      const content = textarea.value;
      if (!content) {
        // 진행 중이던 이전 요청의 응답이 나중에 도착해도 무시되도록 토큰을 갱신하고,
        // 스피너도 즉시 정리한다(그렇지 않으면 비운 미리보기에 stale 응답이 다시 그려질 수 있다).
        latestRequestToken += 1;
        previewSpinner.style.display = 'none';
        previewPane.innerHTML = '';
        return;
      }

      const requestToken = ++latestRequestToken;
      previewSpinner.style.display = 'inline-block';

      fetch(previewUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `content=${encodeURIComponent(content)}`,
      })
        .then((response) => response.json())
        .then((data) => {
          if (requestToken !== latestRequestToken) {
            return;
          }
          if (data.html !== undefined) {
            previewPane.innerHTML = data.html;
          }
        })
        .catch(() => {
          // 실패 시 마지막으로 성공한 렌더링을 그대로 유지하고, 다음 debounce 사이클에서 재시도한다.
        })
        .finally(() => {
          if (requestToken === latestRequestToken) {
            previewSpinner.style.display = 'none';
          }
        });
    }

    textarea.addEventListener('input', debounce(renderPreview, 300));
    renderPreview();
  });
})();
