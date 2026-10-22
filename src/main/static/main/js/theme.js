(function () {
  var STORAGE_KEY = 'meucascalho-theme';
  var DARK_CLASS = 'dark';
  var html = document.documentElement;
  var toggle = document.getElementById('theme-toggle');

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function setTheme(theme) {
    if (theme === 'dark') {
      html.classList.add(DARK_CLASS);
      html.setAttribute('data-theme', 'dark');
      try {
        localStorage.setItem(STORAGE_KEY, 'dark');
      } catch (e) {}
    } else {
      html.classList.remove(DARK_CLASS);
      html.setAttribute('data-theme', 'light');
      try {
        localStorage.setItem(STORAGE_KEY, 'light');
      } catch (e) {}
    }
    updateButtonLabel();
  }

  function updateButtonLabel() {
    if (!toggle) return;
    var isDark = html.classList.contains(DARK_CLASS);
    toggle.setAttribute('aria-checked', isDark);
    toggle.textContent = isDark ? '☀️' : '🌙';
    toggle.setAttribute('title', isDark ? 'Alternar para tema claro' : 'Alternar para tema escuro');
  }

  function init() {
    var saved = getSavedTheme();
    var theme = saved === 'dark' || (saved === null && getSystemTheme() === 'dark') ? 'dark' : 'light';
    setTheme(theme);

    if (toggle) {
      toggle.addEventListener('click', function () {
        var next = html.classList.contains(DARK_CLASS) ? 'light' : 'dark';
        setTheme(next);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
