import { useRef, useState, useCallback } from 'react';
import { audioToText } from '@/api/interview';

interface TranscriptEntry {
  id: number;
  text: string;
  timestamp: string;
}

export default function CameraTest() {
  const videoRef = useRef<HTMLVideoElement>(null);
  type StatusType = 'info' | 'success' | 'error' | 'recording';
  const [status, setStatus] = useState<{ text: string; type: StatusType }>({ text: '等待操作...', type: 'info' });
  const [asrStatus, setAsrStatus] = useState<{ text: string; type: 'info' | 'success' | 'error' | 'recording' }>({ text: '', type: 'info' });
  const [streamActive, setStreamActive] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [recording, setRecording] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const setStatusSafe = useCallback((text: string, type: 'info' | 'success' | 'error' | 'recording') => {
    setStatus({ text, type });
  }, []);

  const startCamera = async () => {
    try {
      setStatusSafe('正在请求摄像头权限...', 'info');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: true,
      });
      if (videoRef.current) videoRef.current.srcObject = stream;
      streamRef.current = stream;
      setStreamActive(true);
      setStatusSafe('摄像头已启动，画面与音频正常。', 'success');
    } catch (err: unknown) {
      const e = err as DOMException;
      let msg = '摄像头访问失败';
      if (e.name === 'NotAllowedError') msg = '权限被拒绝，请在浏览器地址栏允许摄像头和麦克风访问。';
      else if (e.name === 'NotFoundError') msg = '未检测到摄像头设备。';
      else if (e.name === 'NotReadableError') msg = '摄像头被其他程序占用，请关闭后重试。';
      setStatusSafe(msg, 'error');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
      streamRef.current = null;
      setStreamActive(false);
      setStatusSafe('摄像头已停止。', 'info');
    }
  };

  const startRecording = useCallback(() => {
    if (!streamRef.current) return;
    const audioTrack = streamRef.current.getAudioTracks()[0];
    if (!audioTrack) {
      setAsrStatus({ text: '未检测到音频轨道，请确认浏览器已允许麦克风。', type: 'error' });
      return;
    }
    chunksRef.current = [];
    const audioStream = new MediaStream([audioTrack]);
    const recorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = sendToAsr;
    recorder.start();
    recorderRef.current = recorder;
    setRecording(true);
    setAsrStatus({ text: '录音中...', type: 'recording' });
  }, []);

  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
      setRecording(false);
    }
  }, []);

  const sendToAsr = async () => {
    if (chunksRef.current.length === 0) {
      setAsrStatus({ text: '未录到音频数据。', type: 'error' });
      return;
    }

    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    const uniqueName = `rec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.webm`;
    formData.append('audio_file', blob, uniqueName);

    try {
      const res = await audioToText(formData);
      const data = res.data as { data?: { text?: string }; msg?: string };
      if (data.data?.text) {
        const entry: TranscriptEntry = {
          id: Date.now(),
          text: data.data.text,
          timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        };
        setTranscripts((prev) => [...prev, entry]);
        setAsrStatus({ text: '识别完成。', type: 'success' });
        setTimeout(() => setAsrStatus({ text: '', type: 'info' }), 2000);
      } else {
        setAsrStatus({ text: `识别失败: ${data.msg || '未知错误'}`, type: 'error' });
      }
    } catch {
      setAsrStatus({ text: '网络错误，无法连接 ASR 服务。', type: 'error' });
    }
  };

  return (
    <div className="camera-test-page">
      <h1>模拟面试</h1>
      <p className="subtitle">摄像头画面与语音识别</p>

      <div className="main-layout animate-in">
        <div className="video-panel animate-in">
          <div className="video-container">
            <video ref={videoRef} autoPlay playsInline muted />
            {!streamActive && (
              <div className="placeholder">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9A2.25 2.25 0 0013.5 5.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <span>点击下方按钮启动摄像头</span>
              </div>
            )}
          </div>

          <div className="controls">
            <button className="btn-primary" onClick={startCamera} disabled={streamActive}>启动摄像头</button>
            <button className="btn-danger" onClick={stopCamera} disabled={!streamActive}>停止摄像头</button>
          </div>

          <div className={`status ${status.type}`}>{status.text}</div>

          <button
            className={`record-btn ${recording ? 'recording' : ''}`}
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
            onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
            disabled={!streamActive || recording}
          >
            {recording ? '松开结束录音' : '按住录音'}
          </button>

          {asrStatus.text && <div className={`status ${asrStatus.type}`}>{asrStatus.text}</div>}
        </div>

        <div className="text-panel animate-in">
          <h2>识别结果</h2>
          <div className="transcript-box">
            {transcripts.length === 0 ? (
              <div className="transcript-placeholder">按住录音按钮说话，识别结果将显示在这里。</div>
            ) : (
              transcripts.map((entry) => (
                <div className="transcript-entry" key={entry.id}>
                  <div className="timestamp">{entry.timestamp}</div>
                  <div>{entry.text}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
