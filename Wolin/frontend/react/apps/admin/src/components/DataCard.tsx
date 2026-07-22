import { useState } from 'react';

function flattenEntries(obj: Record<string, unknown>, prefix = ''): [string, string][] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) return flattenEntries(v as Record<string, unknown>, key);
    return [[key, v === null || v === undefined ? '-' : String(v)]];
  });
}

export default function DataCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const entries = flattenEntries(data);
  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const sections = new Map<string, [string, string][]>();
  const topLevel: [string, string][] = [];
  for (const [k, v] of entries) {
    if (k.includes('.')) {
      const [sec, sub] = k.split('.');
      if (!sections.has(sec)) sections.set(sec, []);
      sections.get(sec)!.push([sub, v]);
    } else {
      topLevel.push([k, v]);
    }
  }

  const isScore = (val: string) => /^\d+(\.\d+)?$/.test(val) && parseFloat(val) >= 0 && parseFloat(val) <= 100;

  return (
    <div className="data-card">
      <div className="data-card-title">{title}</div>
      {topLevel.length > 0 && (
        <div className="data-card-meta">
          {topLevel.map(([k, v]) => (
            <div className="data-card-row" key={k}>
              <span className="data-card-key">{k}</span>
              <span className={`data-card-val ${isScore(v) ? 'score' : ''}`}>
                {isScore(v) ? (
                  <>
                    <span className="score-badge">{v}分</span>
                    <span className="score-bar-wrap"><span className="score-bar" style={{ width: `${parseFloat(v)}%` }} /></span>
                  </>
                ) : (
                  <span title={v}>{v}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      {Array.from(sections.entries()).map(([sec, items]) => {
        const isExp = expanded[sec] ?? true;
        return (
          <div className="data-card-section" key={sec}>
            <button className="data-card-section-header" onClick={() => toggle(sec)}>
              <span>{sec}</span>
              <svg className={`chevron ${isExp ? 'rotated' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            {isExp && (
              <div className="data-card-section-body">
                {items.map(([k, v]) => (
                  <div className="data-card-row" key={k}>
                    <span className="data-card-key">{k}</span>
                    <span className={`data-card-val ${isScore(v) ? 'score' : ''}`}>
                      {isScore(v) ? (
                        <>
                          <span className="score-badge">{v}分</span>
                          <span className="score-bar-wrap"><span className="score-bar" style={{ width: `${parseFloat(v)}%` }} /></span>
                        </>
                      ) : (
                        <span title={v}>{v}</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
