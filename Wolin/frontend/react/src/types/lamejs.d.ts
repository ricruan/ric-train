// Wolin/frontend/react/src/types/lamejs.d.ts
declare module 'lamejs' {
  interface Mp3Encoder {
    encodeBuffer(left: Int16Array, right?: Int16Array): Uint8Array;
    flush(): Uint8Array;
  }

  interface Mp3EncoderConstructor {
    new (channels: number, sampleRate: number, kbps: number): Mp3Encoder;
  }

  const lamejs: {
    Mp3Encoder: Mp3EncoderConstructor;
  };

  export default lamejs;
}
