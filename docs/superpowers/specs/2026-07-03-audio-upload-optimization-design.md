# 前端音频文件上传优化设计

## 背景

### 问题
用户在 InterviewAnalysis 页面上传音频文件时，遇到以下问题：
1. 控制台输出大量 `python_multipart` DEBUG 日志
2. 日志打印持续几分钟，影响用户体验
3. 大文件（WAV 格式，5分钟约 50MB）上传等待时间长

### 原因分析
1. DEBUG 日志级别过低，`python_multipart` 库的调试信息被输出
2. WAV 文件未压缩，体积大导致上传慢
3. 缺少上传进度反馈，用户无法感知上传状态

## 目标

1. **识别质量优先** - 确保 ASR 识别准确率不受影响
2. **上传速度快** - 减少用户上传等待时间
3. **用户体验好** - 显示压缩和上传进度

## 约束条件

- 用户上传的音频格式混合（WAV、MP3、M4A 等）
- 需要全浏览器兼容（Chrome、Firefox、Safari、Edge）
- 单次录音时长通常 > 5 分钟
- 音频用于 Qwen ASR 语音识别

## 解决方案

### 方案概述

采用**智能压缩 + 进度反馈**的组合方案：

1. **WAV/大文件** → 前端压缩为 MP3 (64kbps) 后上传
2. **MP3/M4A/小文件** → 直接上传
3. **所有上传** → 显示压缩和上传进度

### 架构图

```
用户选择文件
     │
     ▼
┌─────────────────┐
│ 检测文件类型/大小 │
└─────────────────┘
     │
     ├── WAV/大文件(>10MB) ──▶ [lamejs 压缩] ──▶ [显示进度] ──▶ [上传 MP3]
     │
     └── MP3/M4A/小文件 ───────────────────────▶ [显示进度] ──▶ [上传原始文件]
```

## 详细设计

### 1. 音频压缩模块

**文件**: `src/utils/audioCompressor.ts`

**功能**: 将 WAV 文件压缩为 MP3

**技术方案**:
- 使用 `lamejs` 库进行 MP3 编码
- 使用 Web Audio API 的 `decodeAudioData` 解码 WAV
- 码率: 64kbps（语音识别足够，文件小）

**核心代码**:
```typescript
import lamejs from 'lamejs';

export async function compressWavToMp3(
  file: File, 
  kbps: number = 64
): Promise<Blob> {
  // 1. 读取文件为 ArrayBuffer
  const arrayBuffer = await file.arrayBuffer();
  
  // 2. 解码音频
  const audioContext = new AudioContext();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  
  // 3. 编码为 MP3
  const channels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const mp3encoder = new lamejs.Mp3Encoder(channels, sampleRate, kbps);
  
  const samples = audioBuffer.getChannelData(0);
  const sampleBlockSize = 1152;
  const mp3Data: Uint8Array[] = [];
  
  for (let i = 0; i < samples.length; i += sampleBlockSize) {
    const chunk = samples.subarray(i, i + sampleBlockSize);
    const mp3buf = mp3encoder.encodeBuffer(chunk);
    if (mp3buf.length > 0) mp3Data.push(mp3buf);
  }
  
  const end = mp3encoder.flush();
  if (end.length > 0) mp3Data.push(end);
  
  return new Blob(mp3Data, { type: 'audio/mp3' });
}
```

**压缩效果预估**:
| 原始格式 | 原始大小 | 压缩后 | 压缩耗时 |
|---------|---------|--------|---------|
| WAV 5分钟 | ~50 MB | ~2.5 MB | 5-15秒 |
| WAV 10分钟 | ~100 MB | ~5 MB | 10-30秒 |

### 2. 上传进度 Hook

**文件**: `src/hooks/useFileUpload.ts`

**状态设计**:
```typescript
type UploadState = 
  | { status: 'idle' }
  | { status: 'compressing', progress: number }
  | { status: 'uploading', progress: number }
  | { status: 'success' }
  | { status: 'error', message: string };
```

**核心逻辑**:
```typescript
export function useFileUpload() {
  const [state, setState] = useState<UploadState>({ status: 'idle' });
  
  const upload = async (file: File, apiCall: (formData: FormData) => Promise<any>) => {
    try {
      let uploadFile = file;
      
      // WAV 或大文件需要压缩
      if (file.type === 'audio/wav' || file.size > 10 * 1024 * 1024) {
        setState({ status: 'compressing', progress: 0 });
        uploadFile = await compressWithProgress(file, (progress) => {
          setState({ status: 'compressing', progress });
        });
      }
      
      // 上传文件
      setState({ status: 'uploading', progress: 0 });
      const formData = new FormData();
      formData.append('audio_file', uploadFile, uploadFile.name);
      
      await apiCall(formData, (progress) => {
        setState({ status: 'uploading', progress });
      });
      
      setState({ status: 'success' });
    } catch (error) {
      setState({ status: 'error', message: error.message });
    }
  };
  
  return { state, upload };
}
```

### 3. 进度条组件

**文件**: `src/components/FileUploadProgress.tsx`

**UI 设计**:
```
┌─────────────────────────────────────────┐
│ 🎵 会议录音.wav (48.5 MB)               │
│                                         │
│ ████████████░░░░░░░░  压缩中... 60%     │
│ 或                                       │
│ ████████████████████  上传中... 100%    │
└─────────────────────────────────────────┘
```

**Props**:
```typescript
interface FileUploadProgressProps {
  fileName: string;
  fileSize: number;
  state: UploadState;
}
```

### 4. API 层修改

**文件**: `src/api/analysis.ts`

**修改内容**: 支持上传进度回调

```typescript
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

### 5. 页面集成

**文件**: `src/pages/InterviewAnalysis.tsx`

**修改内容**:
1. 引入 `useFileUpload` Hook
2. 引入 `FileUploadProgress` 组件
3. 替换原有的文件上传逻辑

## 文件结构

```
Wolin/frontend/react/src/
├── utils/
│   └── audioCompressor.ts    ← 新增
├── hooks/
│   └── useFileUpload.ts      ← 新增
├── components/
│   └── FileUploadProgress.tsx ← 新增
├── pages/
│   └── InterviewAnalysis.tsx ← 修改
└── api/
    └── analysis.ts           ← 修改
```

## 依赖

```bash
npm install lamejs
npm install -D @types/lamejs
```

## 后端适配

**已完成的修复**:
1. 日志级别改为 INFO
2. 屏蔽 `python_multipart` 的 DEBUG 日志

**无需其他改动**:
- 后端已支持 MP3 格式
- MIME_TYPES 需要添加 `.mp3` 支持（已存在）

## 测试计划

1. **功能测试**:
   - WAV 文件压缩后上传
   - MP3/M4A 文件直接上传
   - 进度条显示正确

2. **兼容性测试**:
   - Chrome/Edge
   - Firefox
   - Safari

3. **性能测试**:
   - 大文件（>50MB）压缩耗时
   - 上传速度对比

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| lamejs 在 Safari 不兼容 | 测试验证，必要时使用替代方案 |
| 压缩质量影响 ASR | 64kbps 对语音识别足够，可调整 |
| 压缩耗时长 | 显示进度，用户可取消 |

## 实施步骤

1. 安装依赖 `lamejs`
2. 实现 `audioCompressor.ts`
3. 实现 `useFileUpload.ts`
4. 实现 `FileUploadProgress.tsx`
5. 修改 `analysis.ts`
6. 修改 `InterviewAnalysis.tsx`
7. 测试验证
