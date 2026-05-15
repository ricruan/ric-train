export function show(msg: string, type: 'info' | 'success' | 'error') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout((el as any)._timer);
  (el as any)._timer = setTimeout(() => {
    el.classList.remove('show');
  }, 3000);
}
