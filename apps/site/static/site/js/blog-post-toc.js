(function () {
  const HEADING_SELECTOR = 'h2, h3';

  function slugify(text) {
    const slug = text
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9가-힣\s-]/g, '')
      .replace(/\s+/g, '-');
    return slug || 'section';
  }

  function ensureHeadingId(heading, usedIds) {
    if (heading.id) {
      usedIds.add(heading.id);
      return heading.id;
    }
    const base = slugify(heading.textContent);
    let id = base;
    let suffix = 1;
    while (usedIds.has(id)) {
      suffix += 1;
      id = `${base}-${suffix}`;
    }
    usedIds.add(id);
    heading.id = id;
    return id;
  }

  function buildTocLink(heading) {
    const link = document.createElement('a');
    link.href = `#${heading.id}`;
    link.textContent = heading.textContent;
    link.className = `toc-link toc-${heading.tagName.toLowerCase()}`;
    return link;
  }

  function setupScrollSpy(headings, links) {
    const linkByHeadingId = new Map();
    headings.forEach((heading, index) => linkByHeadingId.set(heading.id, links[index]));

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        const activeLink = linkByHeadingId.get(entry.target.id);
        if (!activeLink) {
          return;
        }
        links.forEach((link) => link.classList.remove('active'));
        activeLink.classList.add('active');
      });
    }, { rootMargin: '0px 0px -70% 0px' });

    headings.forEach((heading) => observer.observe(heading));
  }

  function init() {
    const article = document.querySelector('article.prose');
    const desktopWrapper = document.getElementById('post-toc-desktop-wrapper');
    const desktopNav = document.getElementById('post-toc-desktop');
    const mobileWrapper = document.getElementById('post-toc-mobile-wrapper');
    const mobileNav = document.getElementById('post-toc-mobile');
    const toggleButton = document.getElementById('post-toc-toggle');
    if (!article || !desktopWrapper || !desktopNav || !mobileWrapper || !mobileNav || !toggleButton) {
      return;
    }

    const headings = Array.from(article.querySelectorAll(HEADING_SELECTOR));
    if (headings.length === 0) {
      desktopWrapper.style.display = 'none';
      mobileWrapper.style.display = 'none';
      return;
    }

    const usedIds = new Set();
    const desktopLinks = headings.map((heading) => {
      ensureHeadingId(heading, usedIds);
      const desktopLink = buildTocLink(heading);
      const mobileLink = buildTocLink(heading);
      desktopNav.appendChild(desktopLink);
      mobileNav.appendChild(mobileLink);
      return desktopLink;
    });

    setupScrollSpy(headings, desktopLinks);

    toggleButton.setAttribute('aria-controls', mobileNav.id);
    toggleButton.setAttribute('aria-expanded', 'false');
    toggleButton.addEventListener('click', () => {
      mobileNav.classList.toggle('hidden');
      mobileNav.classList.toggle('flex');
      toggleButton.setAttribute('aria-expanded', String(!mobileNav.classList.contains('hidden')));
    });
  }

  init();
})();
