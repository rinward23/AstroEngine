(function () {
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-openapi-src]').forEach(function (container) {
      const src = container.getAttribute('data-openapi-src');
      if (!src) return;
      const redocHost = document.createElement('div');
      redocHost.className = 'openapi-redoc';
      container.appendChild(redocHost);
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js';
      script.onload = function () {
        window.Redoc.init(src, {}, redocHost);
      };
      container.appendChild(script);
    });
  });
})();
