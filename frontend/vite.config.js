import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// In dev, `npm run dev` serves the app on :5173 and proxies /api to the
// FastAPI backend on :8080. In prod you `npm run build` and FastAPI serves
// the dist/ folder itself, so everything is same-origin.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'World Cup 2026 Tracker',
        short_name: 'WC2026',
        description: 'Live qualification, knockout route and title odds for World Cup 2026.',
        theme_color: '#07172b',
        background_color: '#07172b',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Cache the app shell (precache) and serve the last good /api/state
        // response when offline so the tracker still renders.
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/state'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-state',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 32, maxAgeSeconds: 600 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8080' }
  },
  build: { outDir: 'dist' }
})
