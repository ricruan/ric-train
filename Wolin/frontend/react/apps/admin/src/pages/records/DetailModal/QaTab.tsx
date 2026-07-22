import { useState } from 'react';
import type { InterviewRecord } from '@interview/shared';
import SectionHeader from '@/components/SectionHeader';
import CopyableBlock from '@/components/CopyableBlock';
import QaDisplay from '@/components/QaDisplay';

export default function QaTab({ record }: { record: InterviewRecord }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setCollapsed((p) => ({ ...p, [id]: !p[id] }));

  const hasAudio = !!record.audio_text;
  const hasQa = record.qa_pairs && typeof record.qa_pairs === 'object' && Object.keys(record.qa_pairs).length > 0;
  const hasAnalysis = record.qa_analysis && typeof record.qa_analysis === 'object' && Object.keys(record.qa_analysis).length > 0;

  return (
    <div className="detail-tab-content">
      {hasAudio && (
        <>
          <SectionHeader id="audio_text" label="音频转写文本" collapsed={collapsed['audio_text']} onToggle={toggle} />
          {!collapsed['audio_text'] && <CopyableBlock text={record.audio_text!} className="section-body prose" />}
        </>
      )}
      {hasQa && (
        <>
          <SectionHeader id="qa_pairs" label="问答对" collapsed={collapsed['qa_pairs']} onToggle={toggle} />
          {!collapsed['qa_pairs'] && <div className="section-body qa-card"><QaDisplay data={record.qa_pairs!} /></div>}
        </>
      )}
      {hasAnalysis && (
        <>
          <SectionHeader id="qa_analysis" label="问答分析" collapsed={collapsed['qa_analysis']} onToggle={toggle} />
          {!collapsed['qa_analysis'] && <div className="section-body qa-card"><QaDisplay data={record.qa_analysis!} /></div>}
        </>
      )}
      {!hasAudio && !hasQa && !hasAnalysis && <div className="detail-empty">暂无问答数据</div>}
    </div>
  );
}
