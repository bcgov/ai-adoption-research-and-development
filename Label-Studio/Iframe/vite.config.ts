import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/app',
  server: {
    port: 5173,
    proxy: {
      // IMPORTANT: Root path must be proxied to backend for Label Studio navigation
      // This regex matches exactly '/' but not '/app' or other paths
      '^/$': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Proxy API requests to Express backend
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Proxy Label Studio requests to Express backend
      '/ls': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        ws: true,
      },
      // Label Studio assets and pages (referenced without /ls prefix in LS HTML)
      '/static': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/react-app': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/label-studio-frontend': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/dm': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/user': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/projects': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Don't proxy /sw.js - service worker causes scope issues in iframe
      '/data': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/settings': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/organization': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/version': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      '/favicon.ico': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
})
