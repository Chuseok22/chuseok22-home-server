(function () {
  var BAR_ID = 'page-loading-bar';
  // htmx:afterRequest 시점에는 트리거 요소가 이미 DOM에서 제거됐을 수 있다
  // (예: hx-swap="outerHTML"로 요소 자신이 교체되는 경우). event.target.closest()로 다시 찾지 않고,
  // event.detail.requestConfig(요청 하나의 생명주기 동안 유지되는 JS 객체, DOM 노드가 아니므로
  // 스왑에 영향받지 않는다)에 마커를 남겨 해당 요청이 종료될 때만 카운트를 줄인다.
  // 카운터를 쓰는 이유: data-page-transition 요청이 겹쳐 진행 중일 때 하나만 끝나도 진행바가
  // 끝나버리지 않도록, 마지막 요청까지 모두 끝났을 때만 finishBar()를 호출한다.
  var pendingPageTransitionCount = 0;
  // finishBar()가 예약한 opacity fade-out 타임아웃 ID. 이 타임아웃이 실행되기 전에
  // 새 요청이 startBar()를 호출하면 취소해야 한다. 그렇지 않으면 이전 요청의
  // fade-out이 새로 시작된(진행 중인) 진행바를 중간에 사라지게 만든다.
  var hideBarTimeoutId = null;

  function getBar() {
    return document.getElementById(BAR_ID);
  }

  function clearHideBarTimeout() {
    if (hideBarTimeoutId) {
      clearTimeout(hideBarTimeoutId);
      hideBarTimeoutId = null;
    }
  }

  function resetBar() {
    var bar = getBar();
    if (!bar) {
      return;
    }
    clearHideBarTimeout();
    bar.style.transition = 'none';
    bar.style.width = '0%';
    bar.style.opacity = '0';
  }

  function startBar() {
    var bar = getBar();
    if (!bar) {
      return;
    }
    clearHideBarTimeout();
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
    hideBarTimeoutId = window.setTimeout(function () {
      bar.style.opacity = '0';
      hideBarTimeoutId = null;
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
      event.detail.requestConfig.isPageTransition = true;
      pendingPageTransitionCount += 1;
      startBar();
    }
  });

  document.addEventListener('htmx:afterRequest', function (event) {
    if (event.detail.requestConfig && event.detail.requestConfig.isPageTransition) {
      pendingPageTransitionCount = Math.max(0, pendingPageTransitionCount - 1);
      if (pendingPageTransitionCount === 0) {
        finishBar();
      }
    }
  });

  // bfcache(뒤로가기/앞으로가기로 캐시된 페이지 복원)로 돌아오면 진행바가
  // 이전 상태(예: 80% 너비)로 그대로 보일 수 있어 복원 시 항상 리셋한다.
  // bfcache는 JS 상태도 그대로 보존하므로, 카운터도 함께 0으로 되돌리지 않으면
  // 복원 전에 진행 중이던 요청이 끝내 afterRequest를 못 받은 경우 카운터가
  // 고착되어 이후 모든 페이지 전환에서 진행바가 끝나지 않게 된다.
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
      pendingPageTransitionCount = 0;
      resetBar();
    }
  });
})();
