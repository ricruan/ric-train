function InlineCopyIcon({ text }: { text: string }) {
  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(text); } catch { /* ignore */ }
  };
  return (
    <button className="inline-copy-btn" onClick={handleCopy} title="复制">📋</button>
  );
}

export default function QaDisplay({ data }: { data: Record<string, unknown> }) {
  const items = Object.entries(data);
  if (items.length === 0) return <div className="qa-empty">暂无数据</div>;

  if (Array.isArray(data)) {
    return (
      <div className="qa-list">
        {data.map((item, idx) => {
          if (typeof item === 'object' && item !== null) {
            const obj = item as Record<string, unknown>;
            const qText = String(obj.question || obj.q || obj.问题 || '');
            const aText = String(obj.answer || obj.a || obj.回答 || obj.analysis || obj.分析 || '');
            return (
              <div className="qa-item" key={idx}>
                <div className="qa-item-header">
                  <span className="qa-item-index">Q{idx + 1}</span>
                  {qText && <span className="qa-item-question">{qText}</span>}
                </div>
                {aText && (
                  <div className="qa-item-answer-wrap">
                    <div className="qa-item-answer">{aText}</div>
                    <InlineCopyIcon text={aText} />
                  </div>
                )}
                {Object.entries(obj)
                  .filter(([k]) => !['question', 'q', '问题', 'answer', 'a', '回答', 'analysis', '分析'].includes(k))
                  .map(([k, v]) => {
                    const vStr = typeof v === 'object' ? JSON.stringify(v) : String(v);
                    return (
                      <div className="qa-item-row" key={k}>
                        <span className="qa-item-key">{k}</span>
                        <span className="qa-item-value">
                          <span className="text-truncate" title={vStr}>{vStr}</span>
                          {vStr.length > 10 && <InlineCopyIcon text={vStr} />}
                        </span>
                      </div>
                    );
                  })}
              </div>
            );
          }
          return <div className="qa-item" key={idx}>{String(item)}</div>;
        })}
      </div>
    );
  }

  return (
    <div className="qa-list">
      {items.map(([k, v]) => {
        if (typeof v === 'object' && v !== null) {
          const subItems = Object.entries(v as Record<string, unknown>);
          return (
            <div className="qa-item" key={k}>
              <div className="qa-item-header"><span className="qa-item-index">{k}</span></div>
              {subItems.map(([sk, sv]) => {
                const svStr = typeof sv === 'object' ? JSON.stringify(sv) : String(sv);
                return (
                  <div className="qa-item-row" key={`${k}.${sk}`}>
                    <span className="qa-item-key">{sk}</span>
                    <span className="qa-item-value">
                      <span className="text-truncate" title={svStr}>{svStr}</span>
                      {svStr.length > 10 && <InlineCopyIcon text={svStr} />}
                    </span>
                  </div>
                );
              })}
            </div>
          );
        }
        const vStr = String(v);
        return (
          <div className="qa-item" key={k}>
            <div className="qa-item-header"><span className="qa-item-index">{k}</span></div>
            <div className="qa-item-answer-wrap">
              <div className="qa-item-answer">{vStr}</div>
              <InlineCopyIcon text={vStr} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
