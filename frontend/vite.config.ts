import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Vite 配置文件
 * 开发代理指向后端服务，端口设为3000
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:6800',
        changeOrigin: true,
      },
    },
  },
});
