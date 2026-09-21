/* ==========================================================================
   FinTech Toolkit — Shared nav bar + site-wide dark/light theme switch.
   Each page must set `window.FTK_ROOT` (relative path back to the project
   root, e.g. "./" for index.html or "../../" for a page under tools) BEFORE
   loading this script.
   ========================================================================== */
(function(){
  var THEME_KEY = 'ftk-theme';

  function readTheme(){
    try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
  }
  function writeTheme(t){
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
  }
  function applyTheme(t){
    document.documentElement.setAttribute('data-theme', t);
    document.dispatchEvent(new CustomEvent('ftk-theme-change', { detail: t }));
  }

  // Apply saved/default theme as early as possible (default: dark).
  var initialTheme = readTheme() || 'dark';
  applyTheme(initialTheme);

  var ROOT = window.FTK_ROOT || './';
  var TOOLS = [
    { href: ROOT + 'index.html', label: '總覽', key: 'home' },
    { href: ROOT + 'tools/stock-drop/index.html', label: '📉 股價下跌追蹤', key: 'stock-drop' },
    { href: ROOT + 'tools/rebalance/index.html', label: '⚖️ 再平衡計算', key: 'rebalance' },
    { href: ROOT + 'tools/retirement/index.html', label: '🏖️ 退休試算', key: 'retirement' },
    { href: ROOT + 'tools/loan/index.html', label: '💰 貸款投資試算', key: 'loan' },
    { href: ROOT + 'tools/rules/index.html', label: '📜 人生財務守則', key: 'rules' }
  ];

  function buildNav(){
    var currentKey = window.FTK_PAGE || '';

    var nav = document.createElement('div');
    nav.className = 'ftk-nav';

    var linksHtml = TOOLS.map(function(t){
      var activeCls = (t.key === currentKey) ? ' ftk-active' : '';
      return '<a class="ftk-nav-link' + activeCls + '" href="' + t.href + '">' + t.label + '</a>';
    }).join('');

    var backHtml = (currentKey && currentKey !== 'home')
      ? '<a class="ftk-back-btn" href="' + ROOT + 'index.html">← 返回總覽</a>'
      : '';

    nav.innerHTML =
      '<div class="ftk-nav-inner">' +
        '<a class="ftk-brand" href="' + ROOT + 'index.html">FinTech Toolkit</a>' +
        backHtml +
        '<button type="button" class="ftk-burger" aria-label="Menu">☰</button>' +
        '<div class="ftk-nav-links">' + linksHtml +
          '<button type="button" class="ftk-theme-btn" aria-label="Toggle theme"></button>' +
        '</div>' +
      '</div>';

    document.body.insertBefore(nav, document.body.firstChild);

    var burger = nav.querySelector('.ftk-burger');
    var links = nav.querySelector('.ftk-nav-links');
    burger.addEventListener('click', function(){
      links.classList.toggle('ftk-open');
    });

    var themeBtn = nav.querySelector('.ftk-theme-btn');
    function syncThemeBtn(){
      var t = document.documentElement.getAttribute('data-theme');
      themeBtn.textContent = (t === 'light') ? '\u{1F319}' : '\u{2600}\u{FE0F}';
      themeBtn.title = (t === 'light') ? '切換成深色' : '切換成淺色';
    }
    syncThemeBtn();
    themeBtn.addEventListener('click', function(){
      var next = (document.documentElement.getAttribute('data-theme') === 'light') ? 'dark' : 'light';
      writeTheme(next);
      applyTheme(next);
      syncThemeBtn();
    });
  }

  function buildFooter(){
    var footer = document.createElement('div');
    footer.className = 'ftk-footer';
    footer.innerHTML = 'FinTech Toolkit · 個人理財工具箱 · <a href="' + ROOT + 'index.html">回總覽</a>';
    document.body.appendChild(footer);
  }

  function init(){
    buildNav();
    if (window.FTK_NO_FOOTER !== true) buildFooter();
  }

  if (document.body) init();
  else document.addEventListener('DOMContentLoaded', init);
})();
