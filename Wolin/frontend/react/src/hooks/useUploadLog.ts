// Wolin/frontend/react/src/hooks/useUploadLog.ts
import { useState, useCallback, useRef } from 'react';

export interface LogEntry {
  id: number;
  timestamp: string;
  level: 'info' | 'success' | 'error' | 'debug';
  message: string;
}

export function useUploadLog() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const idRef = useRef(0);

  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    const entry: LogEntry = {
      id: idRef.current++,
      timestamp: new Date().toLocaleTimeString(),
      level,
      message,
    };
    setLogs(prev => [...prev.slice(-49), entry]); // 保留最近 50 条
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return { logs, addLog, clearLogs };
}
