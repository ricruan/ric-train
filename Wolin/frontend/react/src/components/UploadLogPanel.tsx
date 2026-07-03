// Wolin/frontend/react/src/components/UploadLogPanel.tsx
import type { LogEntry } from '@/hooks/useUploadLog';

interface UploadLogPanelProps {
  logs: LogEntry[];
  onClear: () => void;
}

const LEVEL_STYLES: Record<LogEntry['level'], { color: string; bg: string; icon: string }> = {
  info: { color: '#1890ff', bg: '#e6f7ff', icon: 'ℹ️' },
  success: { color: '#52c41a', bg: '#f6ffed', icon: '✅' },
  error: { color: '#ff4d4f', bg: '#fff2f0', icon: '❌' },
  debug: { color: '#722ed1', bg: '#f9f0ff', icon: '🔍' },
};

export default function UploadLogPanel({ logs, onClear }: UploadLogPanelProps) {
  if (logs.length === 0) return null;

  return (
    <div style={{
      marginTop: '16px',
      border: '1px solid #e8e8e8',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* 标题栏 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 12px',
        backgroundColor: '#fafafa',
        borderBottom: '1px solid #e8e8e8',
      }}>
        <span style={{ fontSize: '14px', fontWeight: 500 }}>
          📋 上传日志
        </span>
        <button
          onClick={onClear}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: '1px solid #d9d9d9',
            borderRadius: '4px',
            backgroundColor: '#fff',
            cursor: 'pointer',
          }}
        >
          清空
        </button>
      </div>

      {/* 日志列表 */}
      <div style={{
        maxHeight: '200px',
        overflowY: 'auto',
        padding: '8px',
        backgroundColor: '#fff',
        fontFamily: 'monospace',
        fontSize: '12px',
      }}>
        {logs.map(log => {
          const style = LEVEL_STYLES[log.level];
          return (
            <div
              key={log.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                padding: '4px 8px',
                marginBottom: '4px',
                backgroundColor: style.bg,
                borderRadius: '4px',
                gap: '8px',
              }}
            >
              <span>{style.icon}</span>
              <span style={{ color: '#999', flexShrink: 0 }}>[{log.timestamp}]</span>
              <span style={{ color: '#333', wordBreak: 'break-all' }}>{log.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
