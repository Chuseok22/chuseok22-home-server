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

    originalParent.appendChild(container);
    container.appendChild(editorPane);
    container.appendChild(previewPane);
    existingChildren.forEach((node) => editorPane.appendChild(node));

    function renderPreview() {
      const content = textarea.value;
      if (!content) {
        previewPane.innerHTML = '';
        return;
      }

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
          if (data.html !== undefined) {
            previewPane.innerHTML = data.html;
          }
        })
        .catch(() => {
          // 실패 시 마지막으로 성공한 렌더링을 그대로 유지하고, 다음 debounce 사이클에서 재시도한다.
        });
    }

    textarea.addEventListener('input', debounce(renderPreview, 300));
    renderPreview();
  });
})();
