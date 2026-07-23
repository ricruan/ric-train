import { apiClient } from '../api/client.js';

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

interface LogEntry {
  level: LogLevel;
  message: string;
  url: string;
  stack: string;
  timestamp: string;
}

const MAX_BUFFER = 500;
const buffer: LogEntry[] = [];
let backendAvailable = true;

function formatEntry(entry: LogEntry): string {
  const base = `[${entry.timestamp}] [${entry.level}] ${entry.message}`;
  const parts = [base];
  if (entry.url) parts.push(`url=${entry.url}`);
  if (entry.stack) parts.push(`\n  stack: ${entry.stack}`);
  return parts.join(' | ');
}

function pushEntry(entry: LogEntry) {
  buffer.push(entry);
  if (buffer.length > MAX_BUFFER) buffer.shift();

  // 同时打印到浏览器控制台
  const consoleFn =
    entry.level === 'ERROR' ? console.error :
    entry.level === 'WARN' ? console.warn :
    entry.level === 'DEBUG' ? console.debug :
    console.log;
  consoleFn(`[FE-LOG] ${formatEntry(entry)}`);

  // 异步发送到后端（不阻塞）
  if (backendAvailable) {
    apiClient.post('/interview/client-log', [entry]).catch(() => {
      backendAvailable = false;
      // 5秒后重试
      setTimeout(() => { backendAvailable = true; }, 5000);
    });
  }
}

function makeEntry(level: LogLevel, message: string, error?: unknown): LogEntry {
  let stack = '';
  if (error instanceof Error) {
    stack = error.stack || '';
    if (!message) message = error.message;
  } else if (error && typeof error === 'object') {
    try { stack = JSON.stringify(error); } catch { stack = String(error); }
  }
  return {
    level,
    message: message || String(error),
    url: window.location.href,
    stack,
    timestamp: new Date().toISOString(),
  };
}

export const frontendLogger = {
  debug(msg: string, error?: unknown) { pushEntry(makeEntry('DEBUG', msg, error)); },
  info(msg: string, error?: unknown) { pushEntry(makeEntry('INFO', msg, error)); },
  warn(msg: string, error?: unknown) { pushEntry(makeEntry('WARN', msg, error)); },
  error(msg: string, error?: unknown) { pushEntry(makeEntry('ERROR', msg, error)); },

  /** 获取所有日志文本（可用于下载） */
  getLogText(): string {
    return buffer.map(formatEntry).join('\n');
  },

  /** 下载日志文件到本地 */
  downloadLog() {
    const text = this.getLogText();
    if (!text) {
      alert('暂无日志记录');
      return;
    }
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `frontend-log-${new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  },

  /** 清空日志 */
  clear() { buffer.length = 0; },

  /** 获取日志条数 */
  get count() { return buffer.length; },
};

// 捕获全局未处理错误
if (typeof window !== 'undefined') {
  window.addEventListener('error', (e) => {
    frontendLogger.error(`[uncaught] ${e.message}`, e.error);
  });
  window.addEventListener('unhandledrejection', (e) => {
    const msg = e.reason instanceof Error ? e.reason.message : String(e.reason);
    frontendLogger.error(`[unhandled-rejection] ${msg}`, e.reason);
  });
}

/** 检查后端是否可达 */
export async function pingBackend(): Promise<{ ok: boolean; message: string }> {
  try {
    const res = await apiClient.get('/interview/health', { timeout: 5000 });
    if (res.data?.data?.status === 'ok') {
      return { ok: true, message: '后端服务正常' };
    }
    return { ok: false, message: `后端响应异常: ${JSON.stringify(res.data)}` };
  } catch (e: unknown) {
    const err = e as { code?: string; message?: string; response?: { status?: number } };
    if (err.code === 'ECONNREFUSED' || err.code === 'ERR_CONNECTION_REFUSED') {
      return { ok: false, message: '后端服务未启动，请检查后端进程是否运行' };
    }
    if (err.code === 'ERR_CONNECTION_RESET') {
      return { ok: false, message: '后端连接被重置，可能后端已崩溃或端口配置错误' };
    }
    if (err.code === 'ECONNABORTED' || err.code === 'ERR_NETWORK') {
      return { ok: false, message: '无法连接后端，请检查后端是否在运行（Vite proxy 端口是否正确）' };
    }
    if (err.response?.status === 404) {
      return { ok: false, message: '后端可达但路由不存在，请检查 API 前缀配置' };
    }
    return { ok: false, message: `连接后端失败: ${err.message || err.code || '未知错误'}` };
  }
}
