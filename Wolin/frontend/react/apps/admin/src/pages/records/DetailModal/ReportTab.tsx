import { useState } from 'react';
import type { InterviewRecord } from '@interview/shared';
import SectionHeader from '@/components/SectionHeader';
import CopyableBlock from '@/components/CopyableBlock';

const sections = [
  { id: 'analysis_start', label: '报告开篇语', key: 'analysis_start' as const },
  { id: 'resume_analysis', label: '简历分析', key: 'resume_analysis' as const },
  { id: 'interview_evaluation', label: '面试官评价', key: 'interview_evaluation' as const },
  { id: 'self_evaluation', label: '自我评价', key: 'self_evaluation' as const },
  { id: 'analysis_end', label: '报告结束语', key: 'analysis_end' as const },
];

export default function ReportTab({ record }: { record: InterviewRecord }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setCollapsed((p) => ({ ...p, [id]: !p[id] }));

  const activeSections = sections.filter((s) => !!record[s.key]);

  return (
    <div className="detail-tab-content">
      {activeSections.map((s) => (
        <div key={s.id}>
          <SectionHeader id={s.id} label={s.label} defaultCollapsed collapsed={collapsed[s.id]} onToggle={toggle} />
          {!collapsed[s.id] && <CopyableBlock text={record[s.key]!} className="section-body prose" />}
        </div>
      ))}
      {activeSections.length === 0 && <div className="detail-empty">暂无报告内容</div>}
    </div>
  );
}
