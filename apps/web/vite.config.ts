import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// One React app serves the website (/, /about, /team) and the product (/app).
// FastAPI serves the built files in production; in development Vite runs on
// :5173 and proxies /api to FastAPI on :8000, so cookies stay same-origin.
export default defineConfig({
  base: '/',
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'BetterU',
        short_name: 'BetterU',
        description: 'Nutrition and training coach',
        start_url: '/app',
        scope: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#000000',
        icons: [{ src: 'leaf.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
      },
      workbox: {
        // Cache the app shell only; API data is always fetched fresh.
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } },
  },
})
