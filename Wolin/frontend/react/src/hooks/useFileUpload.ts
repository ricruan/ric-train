// Wolin/frontend/react/src/hooks/useFileUpload.ts
import { useState, useCallback } from 'react';
import { compressWavToMp3, shouldCompress, formatFileSize } from '@/utils/audioCompressor';

export type UploadState =
  | { status: 'idle' }
  | { status: 'compressing'; progress: number }
  | { status: 'uploading'; progress: number }
  | { status: 'success' }
  | { status: 'error'; message: string };

type ApiCallFn = (formData: FormData, onProgress?: (percent: number) => void) => Promise<any>;
type LogFn = (level: 'info' | 'success' | 'error' | 'debug', message: string) => void;

export function useFileUpload() {
  const [state, setState] = useState<UploadState>({ status: 'idle' });

  const upload = useCallback(async (
    file: File,
    apiCall: ApiCallFn,
    formDataBuilder?: (formData: FormData, file: File) => void,
    logger?: LogFn
  ) => {
    try {
      let uploadFile = file;
      const fileName = file.name;
      const originalSize = formatFileSize(file.size);

      logger?.('info', `选择文件: ${fileName} (${originalSize})`);

      // 判断是否需要压缩
      if (shouldCompress(file)) {
        logger?.('info', `检测到需要压缩: ${file.type === 'audio/wav' ? 'WAV 格式' : '文件 > 10MB'}`);
        setState({ status: 'compressing', progress: 0 });

        const compressStart = Date.now();
        const compressedBlob = await compressWavToMp3(file, 64, (progress) => {
          setState({ status: 'compressing', progress });
          // 每 20% 记录一次日志
          if (progress % 20 === 0 && progress > 0) {
            logger?.('debug', `压缩进度: ${progress}%`);
          }
        });

        const compressTime = ((Date.now() - compressStart) / 1000).toFixed(1);
        const compressedSize = formatFileSize(compressedBlob.size);
        const ratio = ((1 - compressedBlob.size / file.size) * 100).toFixed(1);

        logger?.('success', `压缩完成: ${originalSize} → ${compressedSize} (${ratio}% 压缩率, ${compressTime}s)`);

        // 创建新的 File 对象，保留原文件名但改为 .mp3 后缀
        const mp3FileName = fileName.replace(/\.[^/.]+$/, '') + '.mp3';
        uploadFile = new File([compressedBlob], mp3FileName, { type: 'audio/mp3' });
      } else {
        logger?.('info', '文件无需压缩，直接上传');
      }

      // 上传文件
      setState({ status: 'uploading', progress: 0 });
      logger?.('info', '开始上传...');

      const formData = new FormData();
      if (formDataBuilder) {
        // 自定义 formData 构建（如添加其他字段）
        formDataBuilder(formData, uploadFile);
      } else {
        formData.append('audio_file', uploadFile, uploadFile.name);
      }

      const uploadStart = Date.now();
      await apiCall(formData, (progress) => {
        setState({ status: 'uploading', progress });
        // 每 25% 记录一次日志
        if (progress % 25 === 0 && progress > 0) {
          logger?.('debug', `上传进度: ${progress}%`);
        }
      });

      const uploadTime = ((Date.now() - uploadStart) / 1000).toFixed(1);
      logger?.('success', `上传完成 (${uploadTime}s)`);

      setState({ status: 'success' });
    } catch (error) {
      const message = error instanceof Error ? error.message : '上传失败';
      logger?.('error', `错误: ${message}`);
      setState({ status: 'error', message });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ status: 'idle' });
  }, []);

  return { state, upload, reset };
}
