import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../page_serving_routers/js/shaders',
    emptyOutDir: true,
  },
  base: '/js/shaders/',
})
