document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const toggles = document.querySelectorAll('.theme-toggle');
  const updateTheme = dark => {
    root.classList.toggle('dark', dark);
    root.style.colorScheme = dark ? 'dark' : 'light';
    toggles.forEach(button => { button.dataset.theme = dark ? 'dark' : 'light'; });
  };
  updateTheme(root.classList.contains('dark'));
  toggles.forEach(button => button.addEventListener('click', () => {
    const dark = !root.classList.contains('dark');
    updateTheme(dark);
    try { localStorage.setItem('wc-color-theme', dark ? 'dark' : 'light'); } catch {}
  }));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    let saved;
    try { saved = localStorage.getItem('wc-color-theme'); } catch {}
    if (!saved && root.dataset.wcThemeDefault === 'system') updateTheme(event.matches);
  });
  const updateHeaderHeight = () => {
    const header = document.querySelector('.page-header');
    if (!header) return;
    const height = `${header.getBoundingClientRect().height}px`;
    root.style.scrollPaddingTop = height;
    root.style.setProperty('--navbar-height', height);
  };
  updateHeaderHeight();
  window.addEventListener('resize', updateHeaderHeight);
  document.querySelectorAll('[data-hb-sidebar-toggle]').forEach(button => {
    button.addEventListener('click', event => {
      event.preventDefault();
      button.parentElement.parentElement.classList.toggle('open');
    });
  });
});
