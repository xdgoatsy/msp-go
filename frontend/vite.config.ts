import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [
          ['babel-plugin-react-compiler', {}],
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-redux': ['@reduxjs/toolkit', 'react-redux'],
          'vendor-motion': ['framer-motion'],
          'vendor-form': ['react-hook-form', '@hookform/resolvers', 'zod'],
          'vendor-http': ['axios'],
          'vendor-date': ['date-fns'],
          'vendor-style-utils': ['clsx', 'tailwind-merge'],
        },
        // 优化文件命名策略
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
    sourcemap: false,
    // 使用 terser 进行更好的压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        // 生产环境移除 console 和 debugger
        drop_console: true,
        drop_debugger: true,
        // 移除未使用的代码
        pure_funcs: ['console.log', 'console.info', 'console.debug', 'console.trace'],
      },
      format: {
        // 移除注释
        comments: false,
      },
    },
    // 设置 chunk 大小警告阈值为 1MB
    chunkSizeWarningLimit: 1000,
    // 报告压缩后的大小
    reportCompressedSize: true,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
