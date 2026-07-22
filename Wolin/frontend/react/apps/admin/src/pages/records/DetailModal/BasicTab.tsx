import type { InterviewRecord } from '@interview/shared';
import CopyUuid from '@/components/CopyUuid';

function statusBadge(s: string) {
  const map: Record<string, string> = { processing: '处理中', completed: '已完成', failed: '失败' };
  return <span className={`status-badge status-${s}`}>{map[s] || s}</span>;
}

function formatTime(val?: string) {
  if (!val) return '-';
  return new Date(val).toLocaleString('zh-CN');
}

function formatDuration(seconds?: number) {
  if (!seconds || seconds <= 0) return '-';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}分${s}秒` : `${s}秒`;
}

export default function BasicTab({ record }: { record: InterviewRecord }) {
  return (
    <div className="detail-tab-content">
      <div className="detail-grid">
        <div className="detail-item"><div className="detail-label">ID</div><div className="detail-value">{record.id}</div></div>
        <div className="detail-item"><div className="detail-label">状态</div><div className="detail-value">{statusBadge(record.status)}</div></div>
        <div className="detail-item full-width">
          <div className="detail-label">UUID</div>
          <div className="detail-value"><CopyUuid text={record.record_uuid || '-'} /></div>
        </div>
        <div className="detail-item"><div className="detail-label">用户姓名</div><div className="detail-value">{record.user_name || '-'}</div></div>
        <div className="detail-item"><div className="detail-label">邮箱</div><div className="detail-value">{record.user_email || '-'}</div></div>
        <div className="detail-item"><div className="detail-label">公司</div><div className="detail-value">{record.company_name || '-'}</div></div>
        <div className="detail-item"><div className="detail-label">音频时长</div><div className="detail-value">{formatDuration(record.audio_duration)}</div></div>
        <div className="detail-item"><div className="detail-label">创建时间</div><div className="detail-value">{formatTime(record.created_at)}</div></div>
        <div className="detail-item"><div className="detail-label">完成时间</div><div className="detail-value">{formatTime(record.completed_at)}</div></div>
        {record.error_msg && (
          <div className="detail-item full-width">
            <div className="detail-label">错误信息</div>
            <div className="detail-value error-text">{record.error_msg}</div>
          </div>
        )}
      </div>
    </div>
  );
}
