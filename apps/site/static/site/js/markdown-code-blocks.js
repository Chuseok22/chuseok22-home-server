(function () {
  function languageLabel(pre) {
    return pre.getAttribute('data-lang') || 'text';
  }

  function buildCopyButton(pre) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'code-block-copy';
    button.textContent = '복사';
    button.addEventListener('click', () => {
      if (!navigator.clipboard) {
        return;
      }
      navigator.clipboard.writeText(pre.textContent).then(() => {
        const original = button.textContent;
        button.textContent = '복사됨';
        window.setTimeout(() => {
          button.textContent = original;
        }, 1200);
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
