(function () {
  function languageLabel(pre) {
    return pre.getAttribute('data-lang') || 'text';
  }

  function buildCopyButton(pre) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'code-block-copy';
    button.textContent = '복사';
    // 클릭 시점이 아니라 최초 생성 시점의 라벨을 원본으로 고정한다 — 클릭 시점의
    // button.textContent를 읽으면, 빠르게 연속 클릭했을 때 아직 복원되지 않은
    // '복사됨'/'복사 실패' 같은 일시적 라벨을 원본으로 잘못 캡처하게 된다.
    const originalLabel = button.textContent;
    let resetTimeoutId = null;

    function scheduleReset() {
      if (resetTimeoutId !== null) {
        window.clearTimeout(resetTimeoutId);
      }
      resetTimeoutId = window.setTimeout(() => {
        button.textContent = originalLabel;
        resetTimeoutId = null;
      }, 1200);
    }

    button.addEventListener('click', () => {
      if (!navigator.clipboard) {
        return;
      }
      navigator.clipboard.writeText(pre.textContent).then(() => {
        button.textContent = '복사됨';
        scheduleReset();
      }).catch(() => {
        button.textContent = '복사 실패';
        scheduleReset();
      });
    });
    return button;
  }

  function buildHeader(pre) {
    const header = document.createElement('div');
    header.className = 'code-block-header';

    const label = document.createElement('span');
    label.className = 'code-block-lang';
    label.textContent = languageLabel(pre);

    header.appendChild(label);
    header.appendChild(buildCopyButton(pre));
    return header;
  }

  document.querySelectorAll('.prose pre:not(.mermaid)').forEach((pre) => {
    pre.parentNode.insertBefore(buildHeader(pre), pre);
  });
})();
