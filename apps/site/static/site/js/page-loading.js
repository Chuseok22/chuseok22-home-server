(function () {
  var BAR_ID = 'page-loading-bar';
  // htmx:afterRequest 시점에는 트리거 요소가 이미 DOM에서 제거됐을 수 있다
  // (예: hx-swap="outerHTML"로 요소 자신이 교체되는 경우). closest()로 다시 찾지 않고
  // beforeRequest에서 세운 플래그만으로 종료 여부를 판단해야 진행바가 멈추지 않는 사고를 막는다.
  var pendingPageTransition = false;

  function getBar() {
    return document.getElementById(BAR_ID);
  }

  function resetBar() {
    var bar = getBar();
    if (!bar) {
      return;
    }
    bar.style.transition = 'none';
    bar.style.width = '0%';
    bar.style.opacity = '0';
  }

  function startBar() {
    var bar = getBar();
    if (!bar) {
      return;
    }
    bar.style.transition = 'none';
    bar.style.width = '0%';
    bar.style.opacity = '1';
    // 강제 reflow로 위 스타일이 적용된 뒤에 트랜지션이 다시 걸리게 한다.
    void bar.offsetWidth;
    bar.style.transition = 'width 400ms ease, opacity 200ms ease';
    bar.style.width = '80%';
  }

  function finishBar() {
    var bar = getBar();
    if (!bar) {
      return;
    }
    bar.style.width = '100%';
    window.setTimeout(function () {
      bar.style.opacity = '0';
    }, 200);
  }

  function isInternalNavigationClick(anchor, event) {
    if (event.defaultPrevented || event.button !== 0) {
      return false;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }
    if (anchor.target && anchor.target !== '' && anchor.target !== '_self') {
      return false;
    }
    if (anchor.hasAttribute('download')) {
      return false;
    }
    var url = new URL(anchor.href, window.location.href);
    if (url.origin !== window.location.origin) {
      return false;
    }
    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
      return false;
    }
    return true;
  }

  document.addEventListener('click', function (event) {
    var anchor = event.target.closest('a[href]');
    if (!anchor || !isInternalNavigationClick(anchor, event)) {
      return;
    }
    startBar();
  });

  document.addEventListener('htmx:beforeRequest', function (event) {
    if (event.target.closest('[data-page-transition]')) {
      pendingPageTransition = true;
      startBar();
    }
  });

  document.addEventListener('htmx:afterRequest', function () {
    if (pendingPageTransition) {
      pendingPageTransition = false;
      finishBar();
    }
  });

  // bfcache(뒤로가기/앞으로가기로 캐시된 페이지 복원)로 돌아오면 진행바가
  // 이전 상태(예: 80% 너비)로 그대로 보일 수 있어 복원 시 항상 리셋한다.
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
      resetBar();
    }
  });
})();
