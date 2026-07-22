import { useState, useEffect } from 'react';
import { fetchRecords, deleteRecord } from '@/api/records';
import { Toast } from '@interview/shared';
import type { InterviewRecord } from '@interview/shared';
import FilterPanel from './FilterPanel';
import RecordTable from './RecordTable';
import RecordFormModal from './RecordFormModal';
import DetailModal from './DetailModal';

type FilterValues = {
  user_name: string;
  company_name: string;
  user_email: string;
  status: string;
  created_at_start: string;
  created_at_end: string;
};

const emptyFilters: FilterValues = {
  user_name: '', company_name: '', user_email: '',
  status: '', created_at_start: '', created_at_end: '',
};

export default function RecordManager() {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<InterviewRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [filters, setFilters] = useState<FilterValues>(emptyFilters);
  const [searchOpen, setSearchOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Form modal
  const [formModal, setFormModal] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [formId, setFormId] = useState<number | null>(null);

  // Detail modal
  const [detailId, setDetailId] = useState<number | null>(null);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);

  useEffect(() => {
    const fetchRecordsFn = async () => {
      setLoading(true);
      const params: Record<string, unknown> = { page, page_size: pageSize };
      for (const [k, v] of Object.entries(filters)) {
        if (v && v.trim()) params[k] = k.includes('date') ? v : v.trim();
      }
      try {
        const res = await fetchRecords(params as any);
        if (res.data.status_code === 200 && res.data.data) {
          setRecords(res.data.data.items);
          setTotal(res.data.data.total);
        }
      } catch {
        Toast.error('加载记录失败');
      } finally {
        setLoading(false);
      }
    };
    fetchRecordsFn();
  }, [page, pageSize, filters, refreshKey]);

  const doSearch = () => { setPage(1); };
  const resetSearch = () => { setFilters(emptyFilters); setPage(1); };
  const handleFilterChange = (key: keyof FilterValues, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const openCreate = () => { setFormMode('create'); setFormId(null); setFormModal(true); };
  const openEdit = (id: number) => {
    setFormMode('edit');
    setFormId(id);
    setFormModal(true);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteRecord(deleteTarget);
      Toast.success('删除成功');
      setRefreshKey(k => k + 1);
    } catch {
      Toast.error('删除失败');
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleFormSuccess = () => {
    setFormModal(false);
    setRefreshKey(k => k + 1);
  };

  return (
    <div className="page manager-page">
      <div className="container">
        <h1 className="title">面试记录管理</h1>

        <FilterPanel
          open={searchOpen}
          onToggle={() => setSearchOpen((p) => !p)}
          values={filters}
          onChange={handleFilterChange}
          onSearch={doSearch}
          onReset={resetSearch}
        />

        <div className="toolbar">
          <span className="record-count">共 <strong>{total}</strong> 条记录</span>
          <button className="btn btn-success" onClick={openCreate}>+ 新增记录</button>
        </div>

        <RecordTable
          records={records}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onViewDetail={(id) => setDetailId(id)}
          onEdit={openEdit}
          onDelete={(id) => setDeleteTarget(id)}
          onPageChange={(p) => setPage(p)}
          onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
        />
      </div>

      {formModal && (
        <RecordFormModal
          mode={formMode}
          recordId={formId}
          onClose={() => setFormModal(false)}
          onSuccess={handleFormSuccess}
        />
      )}

      {detailId && (
        <DetailModal
          recordId={detailId}
          onClose={() => setDetailId(null)}
        />
      )}

      {deleteTarget && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setDeleteTarget(null); }}>
          <div className="modal" style={{ maxWidth: 400 }}>
            <h2 className="modal-title">确认删除</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
              确定要删除此记录吗？此操作不可撤销。
            </p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)}>取消</button>
              <button className="btn btn-danger" onClick={handleDelete}>确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
