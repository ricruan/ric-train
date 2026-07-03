// Wolin/frontend/react/src/hooks/useFileUpload.ts
import { useState, useCallback } from 'react';
import { compressWavToMp3, shouldCompress } from '@/utils/audioCompressor';

export type UploadState =
  | { status: 'idle' }
  | { status: 'compressing'; progress: number }
  | { status: 'uploading'; progress: number }
  | { status: 'success' }
  | { status: 'error'; message: string };

type ApiCallFn = (formData: FormData, onProgress?: (percent: number) => void) => Promise<any>;

export function useFileUpload() {
  const [state, setState] = useState<UploadState>({ status: 'idle' });

  const upload = useCallback(async (
    file: File,
    apiCall: ApiCallFn,
    formDataBuilder?: (formData: FormData, file: File) => void
  ) => {
    try {
      let uploadFile = file;
      const fileName = file.name;

      // 判断是否需要压缩
      if (shouldCompress(file)) {
        setState({ status: 'compressing', progress: 0 });

        const compressedBlob = await compressWavToMp3(file, 64, (progress) => {
          setState({ status: 'compressing', progress });
        });

        // 创建新的 File 对象，保留原文件名但改为 .mp3 后缀
        const mp3FileName = fileName.replace(/\.[^/.]+$/, '') + '.mp3';
        uploadFile = new File([compressedBlob], mp3FileName, { type: 'audio/mp3' });
      }

      // 上传文件
      setState({ status: 'uploading', progress: 0 });

      const formData = new FormData();
      if (formDataBuilder) {
        // 自定义 formData 构建（如添加其他字段）
        formDataBuilder(formData, uploadFile);
      } else {
        formData.append('audio_file', uploadFile, uploadFile.name);
      }

      await apiCall(formData, (progress) => {
        setState({ status: 'uploading', progress });
      });

      setState({ status: 'success' });
    } catch (error) {
      const message = error instanceof Error ? error.message : '上传失败';
      setState({ status: 'error', message });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ status: 'idle' });
  }, []);

  return { state, upload, reset };
}
