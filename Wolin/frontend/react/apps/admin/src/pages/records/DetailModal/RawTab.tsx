import type { InterviewRecord } from '@interview/shared';
import DataCard from '@/components/DataCard';

export default function RawTab({ record }: { record: InterviewRecord }) {
  const hasResume = record.resume_info && typeof record.resume_info === 'object' && Object.keys(record.resume_info).length > 0;
  const hasInterview = record.interview_json && typeof record.interview_json === 'object' && Object.keys(record.interview_json).length > 0;

  return (
    <div className="detail-tab-content raw-tab-content">
      {hasResume && <DataCard title="简历信息" data={record.resume_info!} />}
      {hasInterview && <DataCard title="面试详情" data={record.interview_json!} />}
      {!hasResume && !hasInterview && <div className="detail-empty">暂无原始数据</div>}
    </div>
  );
}
