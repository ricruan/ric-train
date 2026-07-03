# 前端音频文件上传优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 WAV 音频文件前端压缩 + 上传进度显示，将 50MB WAV 文件压缩至 2.5MB 后再上传。

**Architecture:** 使用 lamejs 在浏览器端将 WAV 编码为 MP3 (64kbps)，通过 Axios 的 onUploadProgress 显示上传进度，React Hook 管理压缩和上传状态。

**Tech Stack:** React 18, TypeScript, lamejs, Axios

## Global Constraints

- 全浏览器兼容（Chrome、Firefox、Safari、Edge）
- WAV 或 >10MB 文件需压缩为 MP3 (64kbps)
- MP3/M4A/小文件直接上传
- 显示压缩和上传进度

---

## File Structure

| 文件 | 职责 | 操作 |
|------|------|------|
| `src/utils/audioCompressor.ts` | WAV → MP3 压缩 | 新建 |
| `src/hooks/useFileUpload.ts` | 压缩 + 上传状态管理 | 新建 |
| `src/components/FileUploadProgress.tsx` | 进度条 UI | 新建 |
| `src/api/analysis.ts` | 支持进度回调 | 修改 |
| `src/pages/InterviewAnalysis.tsx` | 集成新组件 | 修改 |

---

### Task 1: 安装依赖

**Files:**
- Modify: `Wolin/frontend/react/package.json`

- [ ] **Step 1: 安装 lamejs 及其类型定义**

```bash
cd Wolin/frontend/react
npm install lamejs
npm install -D @types/lamejs
```

Expected: `package.json` 中出现 `lamejs` 依赖

- [ ] **Step 2: 验证安装**

```bash
cd Wolin/frontend/react
npm list lamejs
```

Expected: 显示 lamejs 版本

- [ ] **Step 3: Commit**

```bash
git add Wolin/frontend/react/package.json Wolin/frontend/react/package-lock.json
git commit -m "chore: add lamejs for audio compression"
```

---

### Task 2: 实现音频压缩工具

**Files:**
- Create: `Wolin/frontend/react/src/utils/audioCompressor.ts`

**Interfaces:**
- Produces: `compressWavToMp3(file: File, kbps?: number, onProgress?: (percent: number) => void): Promise<Blob>`

- [ ] **Step 1: 创建 audioCompressor.ts**

```typescript
// Wolin/frontend/react/src/utils/audioCompressor.ts
import lamejs from 'lamejs';

/**
 * 将 WAV 文件压缩为 MP3
 * @param file - WAV 文件
 * @param kbps - 码率，默认 64kbps
 * @param onProgress - 压缩进度回调 (0-100)
 * @returns MP3 Blob
 */
export async function compressWavToMp3(
  file: File,
  kbps: number = 64,
  onProgress?: (percent: number) => void
): Promise<Blob> {
  // 1. 读取文件为 ArrayBuffer
  const arrayBuffer = await file.arrayBuffer();
  
  // 2. 使用 Web Audio API 解码
  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  const audioContext = new AudioContextClass();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  
  // 3. 获取音频参数
  const channels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const totalSamples = audioBuffer.length;
  
  // 4. 创建 MP3 编码器
  const mp3encoder = new lamejs.Mp3Encoder(channels, sampleRate, kbps);
  
  // 5. 逐块编码
  const sampleBlockSize = 1152;
  const mp3Data: Uint8Array[] = [];
  
  // 处理每个声道
  const channelData: Float32Array[] = [];
  for (let ch = 0; ch < channels; ch++) {
    channelData.push(audioBuffer.getChannelData(ch));
  }
  
  // 编码循环
  let processed = 0;
  for (let i = 0; i < totalSamples; i += sampleBlockSize) {
    const end = Math.min(i + sampleBlockSize, totalSamples);
    
    // 提取当前块的样本
    const chunks: Int16Array[] = [];
    for (let ch = 0; ch < channels; ch++) {
      const channelChunk = channelData[ch].subarray(i, end);
      // Float32 -> Int16
      const int16Chunk = new Int16Array(channelChunk.length);
      for (let j = 0; j < channelChunk.length; j++) {
        const s = Math.max(-1, Math.min(1, channelChunk[j]));
        int16Chunk[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      chunks.push(int16Chunk);
    }
    
    // 编码当前块
    let mp3buf: Uint8Array;
    if (channels === 1) {
      mp3buf = mp3encoder.encodeBuffer(chunks[0]);
    } else {
      mp3buf = mp3encoder.encodeBuffer(chunks[0], chunks[1]);
    }
    
    if (mp3buf.length > 0) {
      mp3Data.push(mp3buf);
    }
    
    // 更新进度
    processed += end - i;
    if (onProgress) {
      const percent = Math.round((processed / totalSamples) * 100);
      onProgress(percent);
    }
    
    // 让出主线程，避免阻塞 UI
    if (i % (sampleBlockSize * 100) === 0) {
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  }
  
  // 6. 刷新编码器
  const end = mp3encoder.flush();
  if (end.length > 0) {
    mp3Data.push(end);
  }
  
  // 7. 创建 Blob
  return new Blob(mp3Data, { type: 'audio/mp3' });
}

/**
 * 判断文件是否需要压缩
 */
export function shouldCompress(file: File): boolean {
  const isWav = file.type === 'audio/wav' || file.name.toLowerCase().endsWith('.wav');
  const isLarge = file.size > 10 * 1024 * 1024; // 10MB
  return isWav || isLarge;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd Wolin/frontend/react
npx tsc --noEmit src/utils/audioCompressor.ts
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add Wolin/frontend/react/src/utils/audioCompressor.ts
git commit -m "feat: add audio compressor utility with progress callback"
```

---

### Task 3: 实现上传进度 Hook

**Files:**
- Create: `Wolin/frontend/react/src/hooks/useFileUpload.ts`

**Interfaces:**
- Consumes: `compressWavToMp3`, `shouldCompress` from `audioCompressor.ts`
- Produces: `useFileUpload()` returns `{ state: UploadState, upload: (file: File, apiCall: Function) => Promise<void>, reset: () => void }`

- [ ] **Step 1: 创建 useFileUpload.ts**

```typescript
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
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd Wolin/frontend/react
npx tsc --noEmit src/hooks/useFileUpload.ts
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add Wolin/frontend/react/src/hooks/useFileUpload.ts
git commit -m "feat: add useFileUpload hook with compression and progress"
```

---

### Task 4: 实现进度条组件

**Files:**
- Create: `Wolin/frontend/react/src/components/FileUploadProgress.tsx`

**Interfaces:**
- Consumes: `UploadState` from `useFileUpload.ts`, `formatFileSize` from `audioCompressor.ts`
- Produces: `<FileUploadProgress fileName={string} fileSize={number} state={UploadState} />`

- [ ] **Step 1: 创建 FileUploadProgress.tsx**

```typescript
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
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd Wolin/frontend/react
npx tsc --noEmit src/components/FileUploadProgress.tsx
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add Wolin/frontend/react/src/components/FileUploadProgress.tsx
git commit -m "feat: add FileUploadProgress component with progress bar"
```

---

### Task 5: 修改 API 层支持进度回调

**Files:**
- Modify: `Wolin/frontend/react/src/api/analysis.ts:1-7`

**Interfaces:**
- Consumes: existing `api` client
- Produces: `submitAnalysis(formData: FormData, onProgress?: (percent: number) => void): Promise<AxiosResponse>`

- [ ] **Step 1: 修改 analysis.ts 添加进度回调**

```typescript
// Wolin/frontend/react/src/api/analysis.ts
import api from './client';

export async function submitAnalysis(
  formData: FormData,
  onProgress?: (progress: number) => void
) {
  return api.post('/interview/interview_analysis', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd Wolin/frontend/react
npx tsc --noEmit src/api/analysis.ts
```

Expected: 无错误输出

- [ ] **Step 3: Commit**

```bash
git add Wolin/frontend/react/src/api/analysis.ts
git commit -m "feat: add upload progress callback to submitAnalysis API"
```

---

### Task 6: 集成到 InterviewAnalysis 页面

**Files:**
- Modify: `Wolin/frontend/react/src/pages/InterviewAnalysis.tsx`

**Interfaces:**
- Consumes: `useFileUpload`, `FileUploadProgress`, `submitAnalysis`

- [ ] **Step 1: 修改 InterviewAnalysis.tsx 的 import 部分**

在文件顶部添加新的 import：

```typescript
import { useFileUpload } from '@/hooks/useFileUpload';
import FileUploadProgress from '@/components/FileUploadProgress';
import { submitAnalysis } from '@/api/analysis';
```

删除不再需要的 import（如果有）：
```typescript
// 删除：import { submitAnalysis } from '@/api/analysis';（已在新 import 中包含）
```

- [ ] **Step 2: 修改 InterviewAnalysis.tsx 的组件逻辑**

在 `InterviewAnalysis` 组件中添加 `useFileUpload` hook：

```typescript
export default function InterviewAnalysis() {
  // ... 现有 state 保持不变 ...
  
  // 新增：使用 useFileUpload hook
  const { state: uploadState, upload, reset: resetUpload } = useFileUpload();
  
  // ... 其他代码 ...
}
```

- [ ] **Step 3: 修改 handleSubmit 函数**

替换原有的 `handleSubmit` 函数，使用新的 `upload` 方法：

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

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
      }
    );

    // 检查上传状态
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
  } catch {
    setResult({ message: '网络错误，请检查网络连接后重试', type: 'error' });
  } finally {
    submittingRef.current = false;
    setLoading(false);
  }
};
```

- [ ] **Step 4: 在 JSX 中添加进度条组件**

在音频文件输入框下方添加进度条：

```tsx
{/* 在音频文件输入框的 form-group 内部，file-input-wrapper 后面添加 */}
{audioFile && (uploadState.status === 'compressing' || uploadState.status === 'uploading' || uploadState.status === 'success' || uploadState.status === 'error') && (
  <FileUploadProgress
    fileName={audioFile.name}
    fileSize={audioFile.size}
    state={uploadState}
  />
)}
```

- [ ] **Step 5: 验证页面渲染**

```bash
cd Wolin/frontend/react
npm run build
```

Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 6: Commit**

```bash
git add Wolin/frontend/react/src/pages/InterviewAnalysis.tsx
git commit -m "feat: integrate audio compression and upload progress in InterviewAnalysis page"
```

---

### Task 7: 手动测试验证

- [ ] **Step 1: 启动前端开发服务器**

```bash
cd Wolin/frontend/react
npm run dev
```

- [ ] **Step 2: 测试 WAV 文件上传**

1. 打开浏览器访问前端页面
2. 导航到"面试分析"页面
3. 选择一个 WAV 文件（建议 > 10MB）
4. 点击"开始分析"
5. 验证：
   - [ ] 显示"压缩中... X%"进度
   - [ ] 压缩完成后显示"上传中... X%"进度
   - [ ] 上传完成后显示"上传完成"

- [ ] **Step 3: 测试 MP3 文件上传**

1. 选择一个 MP3 文件
2. 点击"开始分析"
3. 验证：
   - [ ] 直接显示"上传中... X%"进度（无压缩步骤）
   - [ ] 上传完成后显示"上传完成"

- [ ] **Step 4: 测试浏览器兼容性**

在以下浏览器中重复测试：
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari

- [ ] **Step 5: 检查后端日志**

```bash
# 查看后端日志，确认没有大量 DEBUG 日志
tail -f logs/app.log
```

验证：
- [ ] 没有 `python_multipart` 的 DEBUG 日志
- [ ] 上传请求正常处理

- [ ] **Step 6: 最终 Commit（如有修复）**

```bash
git add -A
git commit -m "fix: address issues found during manual testing"
```

---

## 实施检查清单

完成所有 Task 后，确认以下项目：

- [ ] lamejs 依赖已安装
- [ ] `audioCompressor.ts` 已创建并可正常压缩 WAV
- [ ] `useFileUpload.ts` 已创建，状态管理正常
- [ ] `FileUploadProgress.tsx` 已创建，UI 显示正常
- [ ] `analysis.ts` 支持进度回调
- [ ] `InterviewAnalysis.tsx` 已集成所有新功能
- [ ] 手动测试通过（WAV 压缩、MP3 直传、进度显示）
- [ ] 浏览器兼容性测试通过
- [ ] 后端日志无 DEBUG 噪音
