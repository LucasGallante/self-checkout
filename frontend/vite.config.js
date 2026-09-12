import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/menu': 'http://localhost:8000',
      '/checkout': 'http://localhost:8000',
      '/orders': 'http://localhost:8000',
    },
  },
})
