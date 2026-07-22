interface FilterValues {
  user_name: string;
  company_name: string;
  user_email: string;
  status: string;
  created_at_start: string;
  created_at_end: string;
}

interface FilterPanelProps {
  open: boolean;
  onToggle: () => void;
  values: FilterValues;
  onChange: (key: keyof FilterValues, value: string) => void;
  onSearch: () => void;
  onReset: () => void;
}

export default function FilterPanel({ open, onToggle, values, onChange, onSearch, onReset }: FilterPanelProps) {
  return (
    <>
      <div className="search-toggle-wrap">
        <button className="search-toggle-btn" onClick={onToggle}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          {open ? '收起筛选' : '高级筛选'}
          <span className="search-glow" />
        </button>
      </div>
      <div className={`search-panel ${open ? 'open' : ''}`}>
        <div className="search-row">
          <div className="search-item">
            <label>用户姓名</label>
            <input type="text" value={values.user_name} onChange={(e) => onChange('user_name', e.target.value)} placeholder="模糊搜索" />
          </div>
          <div className="search-item">
            <label>公司名称</label>
            <input type="text" value={values.company_name} onChange={(e) => onChange('company_name', e.target.value)} placeholder="模糊搜索" />
          </div>
          <div className="search-item">
            <label>邮箱</label>
            <input type="text" value={values.user_email} onChange={(e) => onChange('user_email', e.target.value)} placeholder="模糊搜索" />
          </div>
          <div className="search-item">
            <label>状态</label>
            <select value={values.status} onChange={(e) => onChange('status', e.target.value)}>
              <option value="">全部</option>
              <option value="processing">处理中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
            </select>
          </div>
          <div className="search-item">
            <label>创建时间起</label>
            <input type="date" value={values.created_at_start} onChange={(e) => onChange('created_at_start', e.target.value)} />
          </div>
          <div className="search-item">
            <label>创建时间止</label>
            <input type="date" value={values.created_at_end} onChange={(e) => onChange('created_at_end', e.target.value)} />
          </div>
          <div className="search-buttons">
            <button className="btn btn-primary" onClick={onSearch}>搜索</button>
            <button className="btn btn-secondary" onClick={onReset}>重置</button>
          </div>
        </div>
      </div>
    </>
  );
}
