import { useState, useRef } from 'react';
import { submitAnalysis } from '@/api/analysis';
import { useFileUpload } from '@/hooks/useFileUpload';
import { useUploadLog } from '@/hooks/useUploadLog';
import FileUploadProgress from '@/components/FileUploadProgress';
import UploadLogPanel from '@/components/UploadLogPanel';

const IconUpload = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

export default function InterviewAnalysis() {
  const [email, setEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const submittingRef = useRef(false);

  // 新增：使用 useFileUpload hook
  const { state: uploadState, upload, reset: resetUpload } = useFileUpload();
  const { logs, addLog, clearLogs } = useUploadLog();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 防重复提交：ref 比 state 更可靠，不受 React 异步批处理影响
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    setResult(null);

    if (!audioFile || !resumeFile) {
      submittingRef.current = false;
      setLoading(false);
      return;
    }

    const trimmedName = userName.trim();
    const trimmedCompany = companyName.trim();

    if (/^[a-zA-Z\s]+$/.test(trimmedName)) {
      setResult({ message: '用户名不能为纯英文，请输入中文或其他语言', type: 'error' });
      submittingRef.current = false;
      setLoading(false);
      return;
    }
    if (/^[a-zA-Z\s]+$/.test(trimmedCompany)) {
      setResult({ message: '公司名称不能为纯英文，请输入中文或其他语言', type: 'error' });
      submittingRef.current = false;
      setLoading(false);
      return;
    }

    try {
      // 使用新的 upload 方法
      await upload(
        audioFile,
        async (formData, onProgress) => {
          // 添加其他字段
          formData.append('receive_email', email);
          formData.append('user_name', trimmedName);
          formData.append('company_name', trimmedCompany);
          formData.append('resume_file', resumeFile!);

          // 调用 API
          return submitAnalysis(formData, onProgress);
        },
        undefined, // formDataBuilder 使用默认
        addLog // 传入日志函数
      );
    } catch {
      setResult({ message: '网络错误，请检查网络连接后重试', type: 'error' });
      addLog('error', '网络请求失败');
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  };

  // 监听上传状态变化
  const prevStatusRef = useRef(uploadState.status);
  if (uploadState.status !== prevStatusRef.current) {
    prevStatusRef.current = uploadState.status;

    if (uploadState.status === 'success') {
      setResult({ message: '提交成功，分析结果将发送到您的邮箱', type: 'success' });
      setEmail('');
      setUserName('');
      setCompanyName('');
      setAudioFile(null);
      setResumeFile(null);
      resetUpload();
    } else if (uploadState.status === 'error') {
      setResult({ message: uploadState.message, type: 'error' });
    }
  }

  const fileLabel = (file: File | null, fallback: string) =>
    file ? `已选择: ${file.name}` : fallback;

  return (
    <div className="page analysis-page">
      <div className="container glass-card animate-in">
        <h1 className="title">面试分析系统</h1>

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group animate-in">
              <label htmlFor="email">接收邮箱</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="请输入接收分析结果的邮箱" />
            </div>

            <div className="form-group animate-in">
              <label htmlFor="userName">用户名</label>
              <input id="userName" type="text" value={userName} onChange={(e) => setUserName(e.target.value)} required placeholder="请输入用户名" />
            </div>
          </div>

          <div className="form-row full">
            <div className="form-group animate-in">
              <label htmlFor="companyName">公司名称</label>
              <input id="companyName" type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)} required placeholder="请输入公司名称" />
            </div>
          </div>

          <div className="upload-row">
            <div className="form-group animate-in">
              <label>音频文件</label>
              <div className="file-input-wrapper">
                <input type="file" accept="audio/*,.m4a,.m4b,.caf,.aac,.ogg,.flac,.amr" onChange={(e) => setAudioFile(e.target.files?.[0] || null)} className="file-input" id="audioInput" />
                <label htmlFor="audioInput" className={`file-input-label ${audioFile ? 'has-file' : ''}`}>
                  <IconUpload />
                  {fileLabel(audioFile, '点击选择音频文件 (mp3, wav, m4a, caf 等)')}
                </label>
              </div>
              {/* 进度条组件 */}
              {audioFile && (uploadState.status === 'compressing' || uploadState.status === 'uploading' || uploadState.status === 'success' || uploadState.status === 'error') && (
                <FileUploadProgress
                  fileName={audioFile.name}
                  fileSize={audioFile.size}
                  state={uploadState}
                />
              )}
            </div>

            <div className="form-group animate-in">
              <label>简历文件</label>
              <div className="file-input-wrapper">
                <input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} className="file-input" id="resumeInput" />
                <label htmlFor="resumeInput" className={`file-input-label ${resumeFile ? 'has-file' : ''}`}>
                  <IconUpload />
                  {fileLabel(resumeFile, '点击选择简历文件 (PDF, DOC, DOCX)')}
                </label>
              </div>
            </div>
          </div>

          <button type="submit" className="submit-btn animate-in" disabled={loading}>
            {loading ? '⏳ 分析中...' : '开始分析'}
          </button>
        </form>

        {loading && <div className="loading"><span className="loading-spinner" />正在分析中，请稍候...</div>}

        {result && (
          <div className={`result ${result.type} animate-in`}>
            {result.type === 'success' ? '✅ ' : '❌ '}
            {result.message}
          </div>
        )}

        {/* 上传日志面板 */}
        <UploadLogPanel logs={logs} onClear={clearLogs} />
      </div>
    </div>
  );
}
