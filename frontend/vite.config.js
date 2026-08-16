import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// RNF2 — Aplicación Web Progresiva (PWA): instalable desde el móvil sin tiendas.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo-udem.png'],
      manifest: {
        name: 'Gimnasio UdeM — Reservas',
        short_name: 'Gym UdeM',
        description: 'Reserva tu cupo en el gimnasio de la Universidad de Medellín.',
        theme_color: '#CC0000',
        background_color: '#F4F4F6',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'logo-udem.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: 'logo-udem.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: false,
    // Vitest solo corre los *.test.*; los *.spec.* de e2e son de Playwright.
    include: ['src/**/*.test.{js,jsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/**/*.test.{js,jsx}', 'src/test/**', 'src/index.jsx'],
    },
  },
});
