import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
export default defineConfig({
 plugins:[tailwindcss()],
 define:{"process.env.NODE_ENV":JSON.stringify("production")},
 resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},
 build:{outDir:'../admin/ui',emptyOutDir:true,lib:{entry:'src/main.tsx',formats:['es'],fileName:()=> 'admin-ui.js',cssFileName:'admin-ui'},rollupOptions:{output:{assetFileNames:'[name][extname]'}}}
})
