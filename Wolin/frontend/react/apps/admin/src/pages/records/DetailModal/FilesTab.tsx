export default function FilesTab({ urls }: { urls: Record<string, { url: string; label: string }> }) {
  if (Object.keys(urls).length === 0) return <div className="detail-tab-content"><div className="detail-empty">暂无可下载文件</div></div>;

  const iconMap: Record<string, string> = { audio: '🎵', text_origin: '📝', text: '📝', report: '📊', resume: '📄' };

  return (
    <div className="detail-tab-content">
      <div className="file-download-grid">
        {Object.entries(urls).map(([key, info]) => {
          const icon = Object.entries(iconMap).find(([k]) => key.startsWith(k))?.[1] || '📎';
          return (
            <a key={key} className="file-card" href={info.url} target="_blank" rel="noopener noreferrer">
              <span className="file-card-icon">{icon}</span>
              <span className="file-card-label">{info.label}</span>
              <span className="file-card-arrow">↗</span>
            </a>
          );
        })}
      </div>
    </div>
  );
}
