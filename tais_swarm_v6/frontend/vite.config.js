import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/stream': 'http://localhost:8612',
      '/events': 'http://localhost:8612',
      '/status': 'http://localhost:8612',
      '/motes': 'http://localhost:8612',
      '/world': 'http://localhost:8612',
      '/player': 'http://localhost:8612',
      '/save': 'http://localhost:8612',
      '/reset': 'http://localhost:8612',
    },
  },
});
