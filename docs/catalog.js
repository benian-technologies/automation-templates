(() => {
  'use strict';
  const root = document.documentElement;
  const search = document.getElementById('search');
  const links = [...document.querySelectorAll('.template-link')];
  const articles = [...document.querySelectorAll('.template-detail')];
  const filters = [...document.querySelectorAll('.filter')];
  const count = document.getElementById('result-count');
  const emptyIndex = document.getElementById('index-empty');
  const empty = document.getElementById('empty-state');
  const live = document.getElementById('copy-status');
  let category = 'all';
  let selected = '';
  const readHash = () => { try { return decodeURIComponent(location.hash.slice(1)); } catch { return ''; } };
  const findArticle = id => articles.find(article => article.id === id);
  function show(id, updateHash = false, focus = false) {
    const article = findArticle(id);
    if (!article) return;
    selected = id;
    articles.forEach(item => item.classList.toggle('is-selected', item.id === id));
    links.forEach(link => {
      if (link.hash === '#' + id) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    if (updateHash) history.replaceState(null, '', '#' + encodeURIComponent(id));
    if (focus) {
      const heading = article.querySelector('h2');
      heading.focus({preventScroll: true});
      if (window.matchMedia('(max-width: 760px)').matches) article.scrollIntoView({block: 'start'});
    }
  }
  function filter() {
    const terms = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    const visible = links.filter(link => {
      const matches = (category === 'all' || link.dataset.category === category)
        && terms.every(term => link.dataset.search.includes(term));
      link.parentElement.hidden = !matches;
      return matches;
    });
    count.textContent = `${visible.length} ${visible.length === 1 ? 'template' : 'templates'}`;
    emptyIndex.hidden = visible.length > 0;
    empty.hidden = visible.length > 0;
    if (!visible.length) {
      articles.forEach(article => article.classList.remove('is-selected'));
      links.forEach(link => link.removeAttribute('aria-current'));
    } else if (!visible.some(link => link.hash === '#' + selected)) {
      show(visible[0].hash.slice(1));
    } else show(selected);
  }
  links.forEach(link => link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    show(link.hash.slice(1), true, true);
  }));
  filters.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter;
    filters.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    filter();
  }));
  search.addEventListener('input', filter);
  document.querySelectorAll('[data-reset]').forEach(button => button.addEventListener('click', () => {
    search.value = '';
    category = 'all';
    filters.forEach(item => item.setAttribute('aria-pressed', String(item.dataset.filter === 'all')));
    filter();
    search.focus();
  }));
  document.querySelectorAll('.copy-command').forEach(button => button.addEventListener('click', async () => {
    const command = document.getElementById(button.dataset.command).textContent;
    try {
      await navigator.clipboard.writeText(command);
      button.textContent = 'Copied';
      live.textContent = 'Command copied. Run it from the downloaded library folder.';
      setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    } catch {
      live.textContent = 'Clipboard unavailable. Select and copy the command shown beside this button.';
    }
  }));
  window.addEventListener('hashchange', () => {
    const id = readHash();
    const link = links.find(item => item.hash === '#' + id);
    if (!link) return;
    search.value = '';
    category = 'all';
    filters.forEach(item => item.setAttribute('aria-pressed', String(item.dataset.filter === 'all')));
    filter();
    show(id);
  });
  root.classList.add('js');
  const initialId = readHash();
  show(findArticle(initialId) ? initialId : links[0].hash.slice(1));
  filter();
})();
