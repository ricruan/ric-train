import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/interview': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        timeout: 10 * 60 * 1000,
      },
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        timeout: 10 * 60 * 1000,
      },
    },
  },
});
