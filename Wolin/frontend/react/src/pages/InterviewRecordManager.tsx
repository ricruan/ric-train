import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchRecords, fetchRecord, createRecord, updateRecord, deleteRecord, fetchDownloadUrls } from '@/api/records';
import type { InterviewRecord } from '@/types';

type DetailTab = 'basic' | 'files' | 'qa' | 'report' | 'raw';

// Collect all text content from a data tree for bulk copy
function collectText(data: unknown): string[] {
  if (typeof data === 'string') return [data];
  if (typeof data === 'number' || typeof data === 'boolean') return [String(data)];
  if (Array.isArray(data)) return data.flatMap(collectText);
  if (data && typeof data === 'object') return Object.values(data as Record<string, unknown>).flatMap(collectText);
  return [];
}

// Flatten a nested object into key-value pairs for chart rendering
function flattenEntries(obj: Record<string, unknown>, prefix = ''): [string, string][] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) return flattenEntries(v as Record<string, unknown>, key);
    return [[key, v === null || v === undefined ? '-' : String(v)]];
  });
}

// Smart data card: renders flat key-values, score bars, and nested sub-cards
function DataCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const entries = flattenEntries(data);
  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  // Detect nested sections
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
      {/* Top-level key-values: one per row */}
      {topLevel.length > 0 && (
        <div className="data-card-meta">
          {topLevel.map(([k, v]) => (
            <div className="data-card-row" key={k}>
              <span className="data-card-key">{k}</span>
              <span className={`data-card-val ${isScore(v) ? 'score' : ''}`}>
                {isScore(v) ? (
                  <>
                    <span className="score-badge">{v}分</span>
                    <span className="score-bar-wrap">
                      <span className="score-bar" style={{ width: `${parseFloat(v)}%` }} />
                    </span>
                  </>
                ) : (
                  <span title={v}>{v}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      {/* Nested sections */}
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
                          <span className="score-bar-wrap">
                            <span className="score-bar" style={{ width: `${parseFloat(v)}%` }} />
                          </span>
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

// Q&A content renderer: turns nested data into readable blocks
function QaDisplay({ data }: { data: Record<string, unknown> }) {
  const items = Object.entries(data);

  if (items.length === 0) return <div className="qa-empty">暂无数据</div>;

  // If data is an array of Q&A items
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
                {/* Show remaining fields */}
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

  // Flat or nested object — render as labeled blocks
  return (
    <div className="qa-list">
      {items.map(([k, v]) => {
        if (typeof v === 'object' && v !== null) {
          const subItems = Object.entries(v as Record<string, unknown>);
          return (
            <div className="qa-item" key={k}>
              <div className="qa-item-header">
                <span className="qa-item-index">{k}</span>
              </div>
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
            <div className="qa-item-header">
              <span className="qa-item-index">{k}</span>
            </div>
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

// Copy-on-hover block: shows a small copy icon when hovering the content
function CopyableBlock({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [text]);

  return (
    <div className="copyable-wrap">
      <button className="copy-icon-btn" onClick={handleCopy} title="复制内容">
        {copied ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 13l4 4L19 7" /></svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg>
        )}
      </button>
      <div className={className}>{text}</div>
    </div>
  );
}

// Inline copy icon for smaller text elements within Q&A cards
function InlineCopyIcon({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [text]);

  return (
    <button className="inline-copy-btn" onClick={handleCopy} title="复制">
      {copied ? '✓' : '📋'}
    </button>
  );
}

export default function InterviewRecordManager() {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<InterviewRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Search fields
  const [searchUser, setSearchUser] = useState('');
  const [searchCompany, setSearchCompany] = useState('');
  const [searchEmail, setSearchEmail] = useState('');
  const [searchStatus, setSearchStatus] = useState('');
  const [searchDateStart, setSearchDateStart] = useState('');
  const [searchDateEnd, setSearchDateEnd] = useState('');

  // Modal state
  const [formModal, setFormModal] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [formId, setFormId] = useState<number | null>(null);
  const [formUserName, setFormUserName] = useState('');
  const [formUserEmail, setFormUserEmail] = useState('');
  const [formCompany, setFormCompany] = useState('');
  const [formStatus, setFormStatus] = useState('processing');
  const [formErrorMsg, setFormErrorMsg] = useState('');

  // Detail modal
  const [detailModal, setDetailModal] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRecord, setDetailRecord] = useState<InterviewRecord | null>(null);
  const [downloadUrls, setDownloadUrls] = useState<Record<string, { url: string; label: string }>>({});
  const [detailTab, setDetailTab] = useState<DetailTab>('basic');
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const modalBodyRef = useRef<HTMLDivElement>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  const doSearch = useCallback(() => {
    setPage(1);
    loadRecords(1, pageSize);
  }, [pageSize]);

  const loadRecords = async (p: number, ps: number) => {
    setLoading(true);
    const params: Record<string, unknown> = { page: p, page_size: ps };
    if (searchUser.trim()) params.user_name = searchUser.trim();
    if (searchCompany.trim()) params.company_name = searchCompany.trim();
    if (searchEmail.trim()) params.user_email = searchEmail.trim();
    if (searchStatus) params.status = searchStatus;
    if (searchDateStart) params.created_at_start = searchDateStart;
    if (searchDateEnd) params.created_at_end = searchDateEnd;

    try {
      const res = await fetchRecords(params as any);
      if (res.data.status_code === 200 && res.data.data) {
        setRecords(res.data.data.items);
        setTotal(res.data.data.total);
        setPage(res.data.data.page);
        setPageSize(res.data.data.page_size);
      }
    } catch {
      alert('网络错误：加载记录失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords(page, pageSize);
  }, []);

  const goPage = (p: number) => {
    const totalPages = Math.ceil(total / pageSize);
    if (p < 1 || p > totalPages) return;
    setPage(p);
    loadRecords(p, pageSize);
  };

  const changePageSize = (newPs: number) => {
    setPageSize(newPs);
    setPage(1);
    loadRecords(1, newPs);
  };

  const resetSearch = () => {
    setSearchUser('');
    setSearchCompany('');
    setSearchEmail('');
    setSearchStatus('');
    setSearchDateStart('');
    setSearchDateEnd('');
    setPage(1);
    loadRecords(1, pageSize);
  };

  const openCreate = () => {
    setFormMode('create');
    setFormId(null);
    setFormUserName('');
    setFormUserEmail('');
    setFormCompany('');
    setFormStatus('processing');
    setFormErrorMsg('');
    setFormModal(true);
  };

  const openEdit = async (id: number) => {
    try {
      const res = await fetchRecord(id);
      if (res.data.status_code !== 200 || !res.data.data) {
        alert('获取记录失败');
        return;
      }
      const d = res.data.data;
      setFormMode('edit');
      setFormId(d.id);
      setFormUserName(d.user_name || '');
      setFormUserEmail(d.user_email || '');
      setFormCompany(d.company_name || '');
      setFormStatus(d.status || 'processing');
      setFormErrorMsg(d.error_msg || '');
      setFormModal(true);
    } catch {
      alert('网络错误');
    }
  };

  const submitForm = async () => {
    if (!formUserName.trim()) {
      alert('请输入用户姓名');
      return;
    }
    const formData = new FormData();
    formData.append('user_name', formUserName.trim());
    formData.append('user_email', formUserEmail.trim());
    formData.append('company_name', formCompany.trim());
    formData.append('status', formStatus);
    formData.append('error_msg', formErrorMsg.trim());

    try {
      if (formMode === 'edit' && formId) {
        await updateRecord(formId, formData);
      } else {
        await createRecord(formData);
      }
      setFormModal(false);
      loadRecords(page, pageSize);
    } catch {
      alert(`${formMode === 'edit' ? '更新' : '创建'}失败`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此记录？此操作不可恢复。')) return;
    try {
      await deleteRecord(id);
      loadRecords(page, pageSize);
    } catch {
      alert('删除失败');
    }
  };

  const viewDetail = async (id: number) => {
    setDetailLoading(true);
    setDetailTab('basic');
    setCollapsedSections({});
    try {
      const [detailRes, downloadRes] = await Promise.all([
        fetchRecord(id),
        fetchDownloadUrls(id),
      ]);
      if (detailRes.data.status_code !== 200 || !detailRes.data.data) {
        alert('获取详情失败');
        return;
      }
      setDetailRecord(detailRes.data.data);
      if (downloadRes.data.status_code === 200 && downloadRes.data.data) {
        setDownloadUrls(downloadRes.data.data);
      } else {
        setDownloadUrls({});
      }
      setDetailModal(true);
    } catch {
      alert('网络错误');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = useCallback(() => {
    setDetailModal(false);
    setDetailRecord(null);
    setDownloadUrls({});
  }, []);

  const toggleSection = useCallback((section: string) => {
    setCollapsedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const copyToClipboard = useCallback(async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  }, []);

  const formatTime = (val?: string) => {
    if (!val) return '-';
    return new Date(val).toLocaleString('zh-CN');
  };

  const statusBadge = (s: string) => {
    const map: Record<string, string> = { processing: '处理中', completed: '已完成', failed: '失败' };
    return <span className={`status-badge status-${s}`}>{map[s] || s}</span>;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds || seconds <= 0) return '-';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}分${s}秒` : `${s}秒`;
  };

  const detailTabs: { key: DetailTab; label: string; icon: string }[] = [
    { key: 'basic', label: '基本信息', icon: '📋' },
    { key: 'files', label: '文件下载', icon: '📎' },
    { key: 'qa', label: '问答分析', icon: '💬' },
    { key: 'report', label: '报告内容', icon: '📊' },
    { key: 'raw', label: '原始数据', icon: '🔧' },
  ];

  const SectionHeader = ({ id, label, defaultCollapsed = false }: { id: string; label: string; defaultCollapsed?: boolean }) => {
    const collapsed = collapsedSections[id] ?? defaultCollapsed;
    return (
      <button className="section-header" onClick={() => toggleSection(id)}>
        <span className="section-label">{label}</span>
        <svg className={`chevron ${collapsed ? '' : 'rotated'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
    );
  };

  const CopyUuid = ({ text }: { text: string }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
      await copyToClipboard(text, 'UUID');
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
  };

  const totalPages = Math.ceil(total / pageSize);
  const range = 2;
  const pageStart = Math.max(1, page - range);
  const pageEnd = Math.min(totalPages, page + range);

  return (
    <div className="page manager-page">
      <div className="container">
        <h1 className="title">面试记录管理</h1>

        {/* Search Toggle Button */}
        <div className="search-toggle-wrap">
          <button className="search-toggle-btn" onClick={() => setSearchOpen((prev) => !prev)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            {searchOpen ? '收起筛选' : '高级筛选'}
            <span className="search-glow" />
          </button>
        </div>

        {/* Search Panel (collapsible) */}
        <div className={`search-panel ${searchOpen ? 'open' : ''}`}>
          <div className="search-row">
            <div className="search-item">
              <label>用户姓名</label>
              <input type="text" value={searchUser} onChange={(e) => setSearchUser(e.target.value)} placeholder="模糊搜索" />
            </div>
            <div className="search-item">
              <label>公司名称</label>
              <input type="text" value={searchCompany} onChange={(e) => setSearchCompany(e.target.value)} placeholder="模糊搜索" />
            </div>
            <div className="search-item">
              <label>邮箱</label>
              <input type="text" value={searchEmail} onChange={(e) => setSearchEmail(e.target.value)} placeholder="模糊搜索" />
            </div>
            <div className="search-item">
              <label>状态</label>
              <select value={searchStatus} onChange={(e) => setSearchStatus(e.target.value)}>
                <option value="">全部</option>
                <option value="processing">处理中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
              </select>
            </div>
            <div className="search-item">
              <label>创建时间起</label>
              <input type="date" value={searchDateStart} onChange={(e) => setSearchDateStart(e.target.value)} />
            </div>
            <div className="search-item">
              <label>创建时间止</label>
              <input type="date" value={searchDateEnd} onChange={(e) => setSearchDateEnd(e.target.value)} />
            </div>
            <div className="search-buttons">
              <button className="btn btn-primary" onClick={doSearch}>搜索</button>
              <button className="btn btn-secondary" onClick={resetSearch}>重置</button>
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="toolbar">
          <span className="record-count">共 <strong>{total}</strong> 条记录</span>
          <button className="btn btn-success" onClick={openCreate}>+ 新增记录</button>
        </div>

        {/* Loading */}
        {loading && <div className="loading-state">加载中...</div>}

        {/* Empty */}
        {!loading && records.length === 0 && <div className="empty-state"><p>暂无记录</p></div>}

        {/* Table */}
        {!loading && records.length > 0 && (
          <>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>用户姓名</th>
                    <th>邮箱</th>
                    <th>公司</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}</td>
                      <td>{r.user_name || '-'}</td>
                      <td>{r.user_email || '-'}</td>
                      <td>{r.company_name || '-'}</td>
                      <td>{statusBadge(r.status)}</td>
                      <td>{formatTime(r.created_at)}</td>
                      <td>
                        <div className="action-btns">
                          <button className="btn btn-info btn-sm" onClick={() => viewDetail(r.id)}>详情</button>
                          <button className="btn btn-primary btn-sm" onClick={() => openEdit(r.id)}>编辑</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(r.id)}>删除</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination">
              <div className="pagination-info">第 {page} / {totalPages} 页，共 {total} 条</div>
              <div className="pagination-controls">
                <button className="page-btn" disabled={page <= 1} onClick={() => goPage(page - 1)}>上一页</button>
                {pageStart > 1 && (
                  <>
                    <button className="page-btn" onClick={() => goPage(1)}>1</button>
                    <span>…</span>
                  </>
                )}
                {Array.from({ length: pageEnd - pageStart + 1 }, (_, i) => pageStart + i).map((p) => (
                  <button key={p} className={`page-btn ${p === page ? 'active' : ''}`} onClick={() => goPage(p)}>{p}</button>
                ))}
                {pageEnd < totalPages && (
                  <>
                    <span>…</span>
                    <button className="page-btn" onClick={() => goPage(totalPages)}>{totalPages}</button>
                  </>
                )}
                <button className="page-btn" disabled={page >= totalPages} onClick={() => goPage(page + 1)}>下一页</button>
                <select className="page-size-select" value={pageSize} onChange={(e) => changePageSize(Number(e.target.value))}>
                  <option value={10}>10条/页</option>
                  <option value={20}>20条/页</option>
                  <option value={50}>50条/页</option>
                  <option value={100}>100条/页</option>
                </select>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Form Modal */}
      {formModal && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setFormModal(false); }}>
          <div className="modal">
            <h2 className="modal-title">{formMode === 'create' ? '新增记录' : '编辑记录'}</h2>
            <div className="form-grid">
              <div className="form-group">
                <label>用户姓名</label>
                <input type="text" value={formUserName} onChange={(e) => setFormUserName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>邮箱</label>
                <input type="email" value={formUserEmail} onChange={(e) => setFormUserEmail(e.target.value)} />
              </div>
              <div className="form-group">
                <label>公司名称</label>
                <input type="text" value={formCompany} onChange={(e) => setFormCompany(e.target.value)} />
              </div>
              <div className="form-group">
                <label>状态</label>
                <select value={formStatus} onChange={(e) => setFormStatus(e.target.value)}>
                  <option value="processing">处理中</option>
                  <option value="completed">已完成</option>
                  <option value="failed">失败</option>
                </select>
              </div>
              <div className="form-group full-width">
                <label>错误信息</label>
                <textarea value={formErrorMsg} onChange={(e) => setFormErrorMsg(e.target.value)} rows={2} />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setFormModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={submitForm}>保存</button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {detailModal && detailRecord && (
        <div className="modal-overlay active detail-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeDetail(); }}>
          <div className="modal detail-modal">
            <h2 className="modal-title">记录详情</h2>

            {/* Tab Navigation */}
            <div className="detail-tabs">
              {detailTabs.map((tab) => {
                const showFiles = tab.key === 'files' && Object.keys(downloadUrls).length === 0;
                return (
                  <button
                    key={tab.key}
                    className={`detail-tab ${detailTab === tab.key ? 'active' : ''}`}
                    onClick={() => setDetailTab(tab.key)}
                    disabled={showFiles}
                  >
                    <span className="detail-tab-icon">{tab.icon}</span>
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Tab Content */}
            <div className="detail-body" ref={modalBodyRef}>
              {detailLoading ? (
                <div className="detail-loading">
                  <span className="loading-spinner" />加载中...
                </div>
              ) : (
                <>
                  {/* Basic Info Tab */}
                  {detailTab === 'basic' && (
                <div className="detail-tab-content">
                  <div className="detail-grid">
                    <div className="detail-item">
                      <div className="detail-label">ID</div>
                      <div className="detail-value">{detailRecord.id}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">状态</div>
                      <div className="detail-value">{statusBadge(detailRecord.status)}</div>
                    </div>
                    <div className="detail-item full-width">
                      <div className="detail-label">UUID</div>
                      <div className="detail-value">
                        <CopyUuid text={detailRecord.record_uuid || '-'} />
                      </div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">用户姓名</div>
                      <div className="detail-value">{detailRecord.user_name || '-'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">邮箱</div>
                      <div className="detail-value">{detailRecord.user_email || '-'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">公司</div>
                      <div className="detail-value">{detailRecord.company_name || '-'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">音频时长</div>
                      <div className="detail-value">{formatDuration(detailRecord.audio_duration)}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">创建时间</div>
                      <div className="detail-value">{formatTime(detailRecord.created_at)}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">完成时间</div>
                      <div className="detail-value">{formatTime(detailRecord.completed_at)}</div>
                    </div>
                    {detailRecord.error_msg && (
                      <div className="detail-item full-width">
                        <div className="detail-label">错误信息</div>
                        <div className="detail-value error-text">{detailRecord.error_msg}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Files Tab */}
              {detailTab === 'files' && (
                <div className="detail-tab-content">
                  {Object.keys(downloadUrls).length === 0 ? (
                    <div className="detail-empty">暂无可下载文件</div>
                  ) : (
                    <div className="file-download-grid">
                      {Object.entries(downloadUrls).map(([key, info]) => {
                        const iconMap: Record<string, string> = { audio: '🎵', text: '📝', report: '📊', resume: '📄' };
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
                  )}
                </div>
              )}

              {/* Q&A Tab */}
              {detailTab === 'qa' && (
                <div className="detail-tab-content">
                  {detailRecord.audio_text && (
                    <>
                      <SectionHeader id="audio_text" label="音频转写文本" />
                      {!collapsedSections['audio_text'] && (
                        <CopyableBlock text={detailRecord.audio_text} className="section-body prose" />
                      )}
                    </>
                  )}

                  {detailRecord.qa_pairs && typeof detailRecord.qa_pairs === 'object' && Object.keys(detailRecord.qa_pairs).length > 0 && (
                    <>
                      <SectionHeader id="qa_pairs" label="问答对" />
                      {!collapsedSections['qa_pairs'] && (
                        <div className="section-body qa-card">
                          <QaDisplay data={detailRecord.qa_pairs} />
                        </div>
                      )}
                    </>
                  )}

                  {detailRecord.qa_analysis && typeof detailRecord.qa_analysis === 'object' && Object.keys(detailRecord.qa_analysis).length > 0 && (
                    <>
                      <SectionHeader id="qa_analysis" label="问答分析" />
                      {!collapsedSections['qa_analysis'] && (
                        <div className="section-body qa-card">
                          <QaDisplay data={detailRecord.qa_analysis} />
                        </div>
                      )}
                    </>
                  )}

                  {!detailRecord.audio_text && !detailRecord.qa_pairs && !detailRecord.qa_analysis && (
                    <div className="detail-empty">暂无问答数据</div>
                  )}
                </div>
              )}

              {/* Report Tab */}
              {detailTab === 'report' && (
                <div className="detail-tab-content">
                  {[
                    { id: 'analysis_start', label: '报告开篇语', val: detailRecord.analysis_start },
                    { id: 'resume_analysis', label: '简历分析', val: detailRecord.resume_analysis },
                    { id: 'interview_evaluation', label: '面试官评价', val: detailRecord.interview_evaluation },
                    { id: 'self_evaluation', label: '自我评价', val: detailRecord.self_evaluation },
                    { id: 'analysis_end', label: '报告结束语', val: detailRecord.analysis_end },
                  ].filter((s) => !!s.val).map((s) => (
                    <div key={s.id}>
                      <SectionHeader id={s.id} label={s.label} defaultCollapsed />
                      {!collapsedSections[s.id] && (
                        <CopyableBlock text={s.val} className="section-body prose" />
                      )}
                    </div>
                  ))}

                  {!detailRecord.analysis_start && !detailRecord.resume_analysis && !detailRecord.interview_evaluation && !detailRecord.self_evaluation && !detailRecord.analysis_end && (
                    <div className="detail-empty">暂无报告内容</div>
                  )}
                </div>
              )}

              {/* Raw Data Tab */}
              {detailTab === 'raw' && (
                <div className="detail-tab-content raw-tab-content">
                  {detailRecord.resume_info && typeof detailRecord.resume_info === 'object' && Object.keys(detailRecord.resume_info).length > 0 && (
                    <DataCard title="简历信息" data={detailRecord.resume_info} />
                  )}
                  {detailRecord.interview_json && typeof detailRecord.interview_json === 'object' && Object.keys(detailRecord.interview_json).length > 0 && (
                    <DataCard title="面试详情" data={detailRecord.interview_json} />
                  )}
                  {!detailRecord.resume_info && !detailRecord.interview_json && (
                    <div className="detail-empty">暂无原始数据</div>
                  )}
                </div>
              )}
                </>
              )}
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={closeDetail}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
