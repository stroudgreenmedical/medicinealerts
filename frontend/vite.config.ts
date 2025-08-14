import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Skip type checking during build for faster deployment
    rollupOptions: {
      onwarn(warning, warn) {
        // Ignore specific warnings to avoid build failures
        if (warning.code === 'UNUSED_EXTERNAL_IMPORT') return
        warn(warning)
      }
    }
  },
  esbuild: {
    // Skip type checking in esbuild for faster builds
    logOverride: { 'this-is-undefined-in-esm': 'silent' }
  }
})
