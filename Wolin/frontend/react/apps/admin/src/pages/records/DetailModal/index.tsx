import { useState, useEffect } from 'react';
import { fetchRecord, fetchDownloadUrls } from '@/api/records';
import { Toast } from '@interview/shared';
import type { InterviewRecord } from '@interview/shared';
import BasicTab from './BasicTab';
import FilesTab from './FilesTab';
import QaTab from './QaTab';
import ReportTab from './ReportTab';
import RawTab from './RawTab';

type DetailTab = 'basic' | 'files' | 'qa' | 'report' | 'raw';

const tabs: { key: DetailTab; label: string; icon: string }[] = [
  { key: 'basic', label: '基本信息', icon: '📋' },
  { key: 'files', label: '文件下载', icon: '📎' },
  { key: 'qa', label: '问答分析', icon: '💬' },
  { key: 'report', label: '报告内容', icon: '📊' },
  { key: 'raw', label: '原始数据', icon: '🔧' },
];

interface Props {
  recordId: number;
  onClose: () => void;
}

export default function DetailModal({ recordId, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState<InterviewRecord | null>(null);
  const [downloadUrls, setDownloadUrls] = useState<Record<string, { url: string; label: string }>>({});
  const [activeTab, setActiveTab] = useState<DetailTab>('basic');

  useEffect(() => {
    Promise.all([fetchRecord(recordId), fetchDownloadUrls(recordId)])
      .then(([detailRes, downloadRes]) => {
        if (detailRes.data.status_code === 200 && detailRes.data.data) {
          setRecord(detailRes.data.data);
        } else {
          Toast.error('获取详情失败');
        }
        if (downloadRes.data.status_code === 200 && downloadRes.data.data) {
          setDownloadUrls(downloadRes.data.data);
        }
      })
      .catch(() => Toast.error('网络错误'))
      .finally(() => setLoading(false));
  }, [recordId]);

  return (
    <div className="modal-overlay active detail-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal detail-modal">
        <h2 className="modal-title">记录详情</h2>
        <div className="detail-tabs">
          {tabs.map((tab) => {
            const disabled = tab.key === 'files' && Object.keys(downloadUrls).length === 0;
            return (
              <button
                key={tab.key}
                className={`detail-tab ${activeTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
                disabled={disabled}
              >
                <span className="detail-tab-icon">{tab.icon}</span>
                {tab.label}
              </button>
            );
          })}
        </div>
        <div className="detail-body">
          {loading ? (
            <div className="detail-loading"><span className="loading-spinner" />加载中...</div>
          ) : record ? (
            <>
              {activeTab === 'basic' && <BasicTab record={record} />}
              {activeTab === 'files' && <FilesTab urls={downloadUrls} />}
              {activeTab === 'qa' && <QaTab record={record} />}
              {activeTab === 'report' && <ReportTab record={record} />}
              {activeTab === 'raw' && <RawTab record={record} />}
            </>
          ) : null}
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  );
}
