import { defineConfig } from 'vite';
export default defineConfig({
  server: { host: '127.0.0.1', proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { chunkSizeWarningLimit: 6000, rollupOptions: { input: ['index.html', 'enclosure.html'] } },
});
