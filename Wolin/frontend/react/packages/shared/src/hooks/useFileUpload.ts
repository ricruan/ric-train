import { useState, useCallback } from 'react';

export type UploadState =
  | { status: 'idle' }
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
      setState({ status: 'uploading', progress: 0 });

      const formData = new FormData();
      if (formDataBuilder) {
        formDataBuilder(formData, file);
      } else {
        formData.append('audio_file', file, file.name);
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
