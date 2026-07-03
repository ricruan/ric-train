// Wolin/frontend/react/src/components/FileUploadProgress.tsx
import { formatFileSize } from '@/utils/audioCompressor';
import type { UploadState } from '@/hooks/useFileUpload';

interface FileUploadProgressProps {
  fileName: string;
  fileSize: number;
  state: UploadState;
}

export default function FileUploadProgress({ fileName, fileSize, state }: FileUploadProgressProps) {
  const getProgressText = () => {
    switch (state.status) {
      case 'compressing':
        return `压缩中... ${state.progress}%`;
      case 'uploading':
        return `上传中... ${state.progress}%`;
      case 'success':
        return '上传完成';
      case 'error':
        return state.message;
      default:
        return '';
    }
  };

  const getProgressPercent = () => {
    if (state.status === 'compressing' || state.status === 'uploading') {
      return state.progress;
    }
    if (state.status === 'success') return 100;
    return 0;
  };

  const getProgressColor = () => {
    switch (state.status) {
      case 'compressing':
        return '#1890ff'; // 蓝色
      case 'uploading':
        return '#52c41a'; // 绿色
      case 'success':
        return '#52c41a';
      case 'error':
        return '#ff4d4f'; // 红色
      default:
        return '#d9d9d9';
    }
  };

  const isActive = state.status === 'compressing' || state.status === 'uploading';
  const isError = state.status === 'error';

  return (
    <div style={{
      padding: '12px 16px',
      borderRadius: '8px',
      backgroundColor: isError ? '#fff2f0' : '#fafafa',
      border: `1px solid ${isError ? '#ffccc7' : '#e8e8e8'}`,
      marginTop: '8px',
    }}>
      {/* 文件名和大小 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '14px', color: '#333' }}>
          🎵 {fileName}
        </span>
        <span style={{ fontSize: '12px', color: '#999' }}>
          {formatFileSize(fileSize)}
        </span>
      </div>

      {/* 进度条 */}
      <div style={{
        height: '8px',
        backgroundColor: '#e8e8e8',
        borderRadius: '4px',
        overflow: 'hidden',
        marginBottom: '8px',
      }}>
        <div
          style={{
            width: `${getProgressPercent()}%`,
            height: '100%',
            backgroundColor: getProgressColor(),
            borderRadius: '4px',
            transition: isActive ? 'width 0.3s ease' : 'none',
          }}
        />
      </div>

      {/* 状态文字 */}
      <div style={{
        fontSize: '12px',
        color: isError ? '#ff4d4f' : '#666',
        textAlign: 'center',
      }}>
        {getProgressText()}
      </div>
    </div>
  );
}
