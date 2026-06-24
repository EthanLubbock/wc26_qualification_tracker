import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, `npm run dev` serves the app on :5173 and proxies /api to the
// FastAPI backend on :8080. In prod you `npm run build` and FastAPI serves
// the dist/ folder itself, so everything is same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8080' }
  },
  build: { outDir: 'dist' }
})
