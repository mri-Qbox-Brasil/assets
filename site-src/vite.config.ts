import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-root-assets',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = req.originalUrl || req.url;
          if (!url) return next();

          // Serve manifest and all image directories from repo root
          const servedPaths = [
            '/manifest.json',
            '/assets/', '/branding/', '/clothing/', '/dui/', '/props/',
            '/char/', '/faces/', '/parents/', '/ps-housing/'
          ];

          if (servedPaths.some(p => url === p || url.startsWith(p))) {
             const filePath = path.resolve(__dirname, '..', url.slice(1)); // Remove leading slash
             try {
                if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
                   const ext = path.extname(filePath).toLowerCase();
                   const mimeTypes: Record<string, string> = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.svg': 'image/svg+xml',
                        '.json': 'application/json',
                        '.webp': 'image/webp',
                        '.mp4': 'video/mp4',
                        '.webm': 'video/webm',
                        '.psd': 'application/octet-stream'
                   };
                   res.setHeader('Content-Type', mimeTypes[ext] || 'application/octet-stream');
                   fs.createReadStream(filePath).pipe(res);
                   return;
                }
             } catch (e) {
                 console.error("Error serving asset:", e);
             }
          }
          next();
        });
      }
    }
  ],
  server: {
      fs: {
          allow: ['..']
      }
  },
  build: {
    outDir: '../', // Build to repository root
    emptyOutDir: false, // CRITICAL: Do not delete existing files in root (images, etc)
    rollupOptions: {
        output: {
            entryFileNames: 'dist/[name]-[hash].js',
            chunkFileNames: 'dist/[name]-[hash].js',
            assetFileNames: 'dist/[name]-[hash].[ext]'
        }
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
