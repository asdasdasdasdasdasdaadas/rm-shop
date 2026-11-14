import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
  plugins: [tailwindcss()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../admin/ui",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: fileURLToPath(new URL("./src/main.tsx", import.meta.url)),
      output: {
        entryFileNames: "admin-ui.js",
        assetFileNames: "admin-ui.[ext]",
        // Sections load on demand; the hash in the name means a deploy never serves a stale piece.
        chunkFileNames: "chunks/[name]-[hash].js",
        // Libraries change rarely, so browsers keep them between admin updates. One file on purpose:
        // splitting them further makes chunks import each other in a loop, which breaks at load time.
        manualChunks(id) {
          return id.includes("node_modules") ? "vendor" : undefined;
        },
      },
    },
  },
});
