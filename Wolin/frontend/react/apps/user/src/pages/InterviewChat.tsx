import { useRef, useState, useCallback, useEffect } from 'react';
import { getInterviewQuestions, submitAnswer } from '@/api/interview';
import { Toast, type InterviewQuestion } from '@interview/shared';

interface Message {
  id: number;
  type: 'interviewer' | 'user' | 'system';
  text: string;
  status?: string;
}

export default function InterviewChat() {
  const [uuid, setUuid] = useState('');
  const [camReady, setCamReady] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [questionsLoaded, setQuestionsLoaded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [recording, setRecording] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const questionsRef = useRef<InterviewQuestion[]>([]);
  const currentQRef = useRef(0);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const recordUuidRef = useRef('');
  const isPlayingRef = useRef(false);

  const scrollDown = useCallback(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, []);

  // Auto-start camera on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: true,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        setCamReady(true);
      } catch {
        if (!cancelled) setCamReady(false);
      }
    })();
    return () => {
      cancelled = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (chatStarted && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [chatStarted]);

  const startChat = async () => {
    const trimmed = uuid.trim();
    if (!streamRef.current) {
      Toast.error('摄像头未授权，无法开始面试');
      return;
    }
    if (!trimmed) {
      Toast.error('请输入 UUID');
      return;
    }

    setLoading(true);
    recordUuidRef.current = trimmed;

    try {
      const res = await getInterviewQuestions(trimmed);
      const qs = res.data.data;
      if (qs && qs.length > 0) {
        questionsRef.current = qs;
        currentQRef.current = 0;
        setChatStarted(true);
        setQuestionsLoaded(true);
      } else {
        Toast.error('未找到面试问题，请检查 UUID');
      }
    } catch {
      Toast.error('网络错误，无法加载问题');
    } finally {
      setLoading(false);
    }
  };

  const showNextQuestion = useCallback(() => {
    if (currentQRef.current >= questionsRef.current.length) {
      setMessages((prev) => [...prev, { id: Date.now(), type: 'system', text: '面试已结束，感谢参与！' }]);
      return;
    }
    const q = questionsRef.current[currentQRef.current];
    setMessages((prev) => [...prev, { id: Date.now(), type: 'interviewer', text: q.question, status: '语音播放中...' }]);
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }

    if (q.audio_url) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      isPlayingRef.current = true;
      const audio = new Audio(q.audio_url);
      audioPlayerRef.current = audio;

      const clearPlaying = () => { isPlayingRef.current = false; audioPlayerRef.current = null; };
      audio.addEventListener('ended', () => {
        setMessages((prev) =>
          prev.map((m) => (m.status === '语音播放中...' ? { ...m, status: '' } : m))
        );
        clearPlaying();
      });
      audio.addEventListener('error', () => {
        setMessages((prev) =>
          prev.map((m) => (m.status === '语音播放中...' ? { ...m, status: '（语音播放失败，直接显示文字）' } : m))
        );
        clearPlaying();
      });
      audio.play().catch(() => {
        setMessages((prev) =>
          prev.map((m) => (m.status === '语音播放中...' ? { ...m, status: '（语音自动播放被拦截，请点击页面）' } : m))
        );
        clearPlaying();
      });
    }
  }, []);

  const beginInterview = useCallback(() => {
    setQuestionsLoaded(false);
    showNextQuestion();
  }, [showNextQuestion]);

  const startRecording = useCallback(() => {
    if (recording || !streamRef.current) return;
    const audioTrack = streamRef.current.getAudioTracks()[0];
    if (!audioTrack) {
      Toast.error('未检测到音频轨道');
      return;
    }
    chunksRef.current = [];
    const audioStream = new MediaStream([audioTrack]);
    const recorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = handleRecordingComplete;
    recorder.start();
    recorderRef.current = recorder;
    setRecording(true);
  }, [recording]);

  const stopRecording = useCallback(() => {
    if (!recording || !recorderRef.current || recorderRef.current.state === 'inactive') return;
    recorderRef.current.stop();
    setRecording(false);
  }, [recording]);

  const handleRecordingComplete = async () => {
    if (chunksRef.current.length === 0) {
      Toast.error('未录到音频数据');
      return;
    }

    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('answer_audio', blob, `answer_${Date.now()}.webm`);
    formData.append('record_uuid', recordUuidRef.current);

    const q = questionsRef.current[currentQRef.current];
    formData.append('question_text', q.question);
    formData.append('question_tts_path', q.audio_url || '');

    try {
      const res = await submitAnswer(formData);
      const data = res.data as { data?: { answer_text?: string }; msg?: string };
      const answerText = data.data?.answer_text;
      if (answerText) {
        setMessages((prev) => [
          ...prev,
          { id: Date.now(), type: 'user', text: answerText },
        ]);
        currentQRef.current++;
        scrollDown();
        setTimeout(showNextQuestion, 300);
      } else {
        Toast.error(`识别失败: ${data.msg || '未返回文字'}`);
      }
    } catch {
      Toast.error('网络错误，无法提交回答');
    }
  };

  return (
    <div className="page chat-page interview-console">
      <h1 className="console-title">模拟面试对话</h1>
      <p className="subtitle console-subtitle">基于简历问题的交互式面试</p>

      {!chatStarted ? (
        <div className="uuid-section">
          <label htmlFor="uuidInput">面试记录 UUID</label>
          <input
            id="uuidInput"
            type="text"
            value={uuid}
            onChange={(e) => setUuid(e.target.value)}
            placeholder="请输入 record_uuid"
          />
          <button
            className="btn-gradient"
            onClick={startChat}
            disabled={!camReady || loading}
          >
            {loading ? '加载问题中...' : !camReady ? '摄像头未授权' : '开始面试'}
          </button>
          <div className={`cam-hint ${camReady ? 'success' : 'error'}`}>
            {camReady ? '摄像头已就绪' : '摄像头权限被拒绝，请允许后刷新页面'}
          </div>
        </div>
      ) : (
        <div className="content-area">
          <div className="console-layout">
            <div className="console-camera">
              <div className="camera-frame">
                <video ref={videoRef} autoPlay playsInline muted />
                <div className="camera-overlay">
                  <div className="live-badge">
                    <span className="live-dot" />
                    LIVE
                  </div>
                </div>
                <div className="corner corner-tl" />
                <div className="corner corner-tr" />
                <div className="corner corner-bl" />
                <div className="corner corner-br" />
              </div>
              <div className="camera-label">面试过程中摄像头不可关闭</div>
            </div>

            <div className="console-chat">
              <div className="chat-header">
                <span className="header-icon" />
                面试官
              </div>
              <div className="chat-messages" ref={chatMessagesRef}>
                {messages.map((msg) => (
                  <div key={msg.id} className={`msg ${msg.type}`}>
                    {msg.type !== 'system' && (
                      <div className="msg-label">{msg.type === 'interviewer' ? '面试官' : '我'}</div>
                    )}
                    {msg.type === 'system' ? (
                      <div className="sys-msg">{msg.text}</div>
                    ) : (
                      <>
                        <div className={`msg-bubble ${msg.type === 'interviewer' && msg.status === '语音播放中...' ? 'playing' : ''}`}>
                          {msg.status === '语音播放中...' ? '正在播放语音...' : msg.text}
                        </div>
                        {msg.status && <div className="msg-status">{msg.status}</div>}
                      </>
                    )}
                  </div>
                ))}
              </div>
              <div className="record-area">
                {questionsLoaded ? (
                  <div className="confirm-prompt">
                    <div className="confirm-card">
                      <div className="confirm-title">面试官已抵达在线会议室</div>
                      <div className="confirm-sub">请在做好准备后，点击 开始面试 按钮</div>
                    </div>
                    <button className="btn-confirm" onClick={beginInterview}>
                      开始面试
                    </button>
                  </div>
                ) : (
                  <button
                    className="record-btn full"
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    onMouseLeave={stopRecording}
                    onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
                    onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
                    disabled={!camReady || recording || currentQRef.current >= questionsRef.current.length}
                  >
                    {!camReady
                      ? '摄像头未就绪'
                      : currentQRef.current >= questionsRef.current.length
                      ? '面试已完成'
                      : isPlayingRef.current
                      ? '面试官发言中...'
                      : recording
                      ? '松开结束录音'
                      : '按住录音，松开发送'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
