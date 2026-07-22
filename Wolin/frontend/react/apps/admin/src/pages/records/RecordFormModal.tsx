import { useState, useEffect } from 'react';
import { createRecord, updateRecord, fetchRecord } from '@/api/records';
import { Toast } from '@interview/shared';

interface Props {
  mode: 'create' | 'edit';
  recordId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function RecordFormModal({ mode, recordId, onClose, onSuccess }: Props) {
  const [userName, setUserName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [company, setCompany] = useState('');
  const [status, setStatus] = useState('processing');
  const [errorMsg, setErrorMsg] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && recordId) {
      fetchRecord(recordId).then((res) => {
        if (res.data.status_code === 200 && res.data.data) {
          const d = res.data.data;
          setUserName(d.user_name || '');
          setUserEmail(d.user_email || '');
          setCompany(d.company_name || '');
          setStatus(d.status || 'processing');
          setErrorMsg(d.error_msg || '');
        }
      }).catch(() => Toast.error('获取记录失败'));
    }
  }, [mode, recordId]);

  const handleSubmit = async () => {
    if (!userName.trim()) { Toast.error('请输入用户姓名'); return; }
    setSaving(true);
    const formData = new FormData();
    formData.append('user_name', userName.trim());
    formData.append('user_email', userEmail.trim());
    formData.append('company_name', company.trim());
    formData.append('status', status);
    formData.append('error_msg', errorMsg.trim());
    try {
      if (mode === 'edit' && recordId) {
        await updateRecord(recordId, formData);
        Toast.success('更新成功');
      } else {
        await createRecord(formData);
        Toast.success('创建成功');
      }
      onSuccess();
    } catch {
      Toast.error(`${mode === 'edit' ? '更新' : '创建'}失败`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        <h2 className="modal-title">{mode === 'create' ? '新增记录' : '编辑记录'}</h2>
        <div className="form-grid">
          <div className="form-group">
            <label>用户姓名</label>
            <input type="text" value={userName} onChange={(e) => setUserName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>邮箱</label>
            <input type="email" value={userEmail} onChange={(e) => setUserEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label>公司名称</label>
            <input type="text" value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>
          <div className="form-group">
            <label>状态</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="processing">处理中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
            </select>
          </div>
          <div className="form-group full-width">
            <label>错误信息</label>
            <textarea value={errorMsg} onChange={(e) => setErrorMsg(e.target.value)} rows={2} />
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
