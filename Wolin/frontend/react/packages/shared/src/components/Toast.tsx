import { createRoot } from 'react-dom/client';
import { useState, useEffect } from 'react';

type ToastType = 'info' | 'success' | 'error';

interface ToastItem {
  id: number;
  msg: string;
  type: ToastType;
}

let nextId = 0;
let container: HTMLDivElement | null = null;
let listeners: Set<(items: ToastItem[]) => void> = new Set();
let currentItems: ToastItem[] = [];

function notify() {
  listeners.forEach((fn) => fn([...currentItems]));
}

function addToast(msg: string, type: ToastType) {
  const id = ++nextId;
  currentItems = [...currentItems, { id, msg, type }];
  notify();
  setTimeout(() => {
    currentItems = currentItems.filter((t) => t.id !== id);
    notify();
  }, 3000);
}

export const Toast = {
  info: (msg: string) => addToast(msg, 'info'),
  success: (msg: string) => addToast(msg, 'success'),
  error: (msg: string) => addToast(msg, 'error'),
  show: (msg: string, type: ToastType = 'info') => addToast(msg, type),
};

function ToastContainer() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    listeners.add(setItems);
    return () => { listeners.delete(setItems); };
  }, []);

  const iconMap: Record<ToastType, string> = { info: 'ℹ️', success: '✅', error: '❌' };

  return (
    <div className="toast-portal">
      {items.map((item) => (
        <div key={item.id} className={`toast-item toast-${item.type}`}>
          <span className="toast-icon">{iconMap[item.type]}</span>
          <span className="toast-msg">{item.msg}</span>
        </div>
      ))}
    </div>
  );
}

function ensureContainer() {
  if (container) return;
  container = document.createElement('div');
  container.id = 'toast-portal-root';
  document.body.appendChild(container);
  createRoot(container).render(<ToastContainer />);
}

// Auto-init on import
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureContainer);
  } else {
    ensureContainer();
  }
}
