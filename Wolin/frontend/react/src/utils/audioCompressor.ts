// Wolin/frontend/react/src/utils/audioCompressor.ts
// @ts-ignore - lamejs has no default export types
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
  return new Blob(mp3Data.map(arr => arr.buffer as ArrayBuffer), { type: 'audio/mp3' });
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
