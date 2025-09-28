(function () {
  const marker = document.querySelector('meta[name="doc-version"]');
  if (!marker) return;
  const pill = document.createElement('span');
  pill.className = 'version-pill';
  pill.textContent = marker.getAttribute('content');
  const header = document.querySelector('.md-header__title');
  if (header) {
    header.appendChild(pill);
  }
})();
