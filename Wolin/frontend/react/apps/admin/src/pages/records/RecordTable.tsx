import type { InterviewRecord } from '@interview/shared';

interface RecordTableProps {
  records: InterviewRecord[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  onViewDetail: (id: number) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function statusBadge(s: string) {
  const map: Record<string, string> = { processing: '处理中', completed: '已完成', failed: '失败' };
  return <span className={`status-badge status-${s}`}>{map[s] || s}</span>;
}

function formatTime(val?: string) {
  if (!val) return '-';
  return new Date(val).toLocaleString('zh-CN');
}

export default function RecordTable({
  records, loading, total, page, pageSize,
  onViewDetail, onEdit, onDelete, onPageChange, onPageSizeChange,
}: RecordTableProps) {
  const totalPages = Math.ceil(total / pageSize);
  const range = 2;
  const pageStart = Math.max(1, page - range);
  const pageEnd = Math.min(totalPages, page + range);

  if (loading) return <div className="loading-state">加载中...</div>;
  if (records.length === 0) return <div className="empty-state"><p>暂无记录</p></div>;

  return (
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
                    <button className="btn btn-info btn-sm" onClick={() => onViewDetail(r.id)}>详情</button>
                    <button className="btn btn-primary btn-sm" onClick={() => onEdit(r.id)}>编辑</button>
                    <button className="btn btn-danger btn-sm" onClick={() => onDelete(r.id)}>删除</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <div className="pagination-info">第 {page} / {totalPages} 页，共 {total} 条</div>
        <div className="pagination-controls">
          <button className="page-btn" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
          {pageStart > 1 && (
            <>
              <button className="page-btn" onClick={() => onPageChange(1)}>1</button>
              <span>…</span>
            </>
          )}
          {Array.from({ length: pageEnd - pageStart + 1 }, (_, i) => pageStart + i).map((p) => (
            <button key={p} className={`page-btn ${p === page ? 'active' : ''}`} onClick={() => onPageChange(p)}>{p}</button>
          ))}
          {pageEnd < totalPages && (
            <>
              <span>…</span>
              <button className="page-btn" onClick={() => onPageChange(totalPages)}>{totalPages}</button>
            </>
          )}
          <button className="page-btn" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>下一页</button>
          <select className="page-size-select" value={pageSize} onChange={(e) => onPageSizeChange(Number(e.target.value))}>
            <option value={10}>10条/页</option>
            <option value={20}>20条/页</option>
            <option value={50}>50条/页</option>
            <option value={100}>100条/页</option>
          </select>
        </div>
      </div>
    </>
  );
}
