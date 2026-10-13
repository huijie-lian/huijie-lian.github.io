// Keep the existing preference key so returning visitors retain their theme.
(() => {
  const root = document.documentElement;
  let saved;
  try { saved = localStorage.getItem('wc-color-theme'); } catch {}
  const mode = saved || root.dataset.wcThemeDefault || 'light';
  const dark = mode === 'dark' || (mode === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  root.classList.toggle('dark', dark);
  root.style.colorScheme = dark ? 'dark' : 'light';
})();
