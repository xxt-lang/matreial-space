import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 开发期把 /api 代理到本地后端：前端统一用相对路径调用，避免 CORS
    // 后端启动方式见 server/README.md（默认 127.0.0.1:8000）
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // 后端的本地静态资源（上传的图片）
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
