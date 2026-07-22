import { useState } from 'react';

export default function CopyUuid({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(text); }
    catch {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <span className="copy-uuid-wrap">
      <code className="copy-uuid" title={text}>{text}</code>
      <button className="copy-btn" onClick={handleCopy} title="复制">
        {copied ? '✓' : '📋'}
      </button>
    </span>
  );
}
