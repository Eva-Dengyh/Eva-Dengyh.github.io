/* Progressive enhancement: all writing is readable without JavaScript. */
(() => {
  const root = document.querySelector('[data-listing]');
  if (root) setupListing(root);
  const article = document.querySelector('[data-article]');
  if (article) setupArticle(article);

  function setupListing(root) {
    const input = root.querySelector('#search');
    const rows = [...root.querySelectorAll('[data-post]')];
    const buttons = [...root.querySelectorAll('[data-topic-filter]')];
    const status = root.querySelector('#result-count');
    const params = new URLSearchParams(location.search);
    let selected = params.get('topic') || 'all';
    const year = params.get('year') || '';
    if (!buttons.some(button => button.dataset.topicFilter === selected)) selected = 'all';
    input.value = params.get('q') || '';
    function filter() {
      const query = input.value.trim().toLocaleLowerCase();
      let count = 0;
      for (const [index, row] of rows.entries()) {
        row.hidden = !(row.dataset.search.toLocaleLowerCase().includes(query) &&
          (selected === 'all' || row.dataset.topic === selected) &&
          (!year || row.dataset.year === year));
        if (!row.hidden) count++;
        const limit = Number(root.dataset.previewLimit || 0);
        if (limit && !query && selected === 'all' && !year && index >= limit) row.hidden = true;
      }
      for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.topicFilter === selected));
      root.querySelector('#empty').hidden = count !== 0;
      status.textContent = query || selected !== 'all' || year ? `${count} ${status.dataset.unit}${year ? ` · ${year}` : ''}` : '';
      const next = new URL(location.href);
      if (query) next.searchParams.set('q', input.value.trim()); else next.searchParams.delete('q');
      if (selected !== 'all') next.searchParams.set('topic', selected); else next.searchParams.delete('topic');
      history.replaceState(null, '', next);
    }
    input.addEventListener('input', filter);
    for (const button of buttons) button.addEventListener('click', () => { selected = button.dataset.topicFilter; filter(); });
    document.addEventListener('keydown', event => {
      const editable = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
      if (event.key === '/' && !editable && !event.ctrlKey && !event.metaKey && !event.altKey) { event.preventDefault(); input.focus(); }
      if (event.key === 'Escape' && document.activeElement === input) { input.value = ''; filter(); input.blur(); }
    });
    filter();
  }

  function setupArticle(article) {
    for (const link of document.querySelectorAll('a[href^="#section-"]')) link.addEventListener('click', () => {
      for (const other of document.querySelectorAll('.toc a[aria-current]')) other.removeAttribute('aria-current');
      link.setAttribute('aria-current', 'location');
    });
  }
})();
