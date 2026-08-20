import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: [
      'vscode.colors.nyc.mn'
    ],
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:4388',
        changeOrigin: true,
      },
      '/books': {
        target: 'http://localhost:4388',
        changeOrigin: true,
      },
    },
  },
})