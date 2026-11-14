import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
  plugins: [tailwindcss()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  // Where the built files are served: Vite preloads a section's pieces by this path. With "/" it asked for
  // /chunks/..., got 404, and a failed preload fails the section, which reloads the page.
  base: "/admin/static/ui/",
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
        // Code the sections share with the page goes to its own hashed file too. Left in admin-ui.js, the
        // sections would import "../admin-ui.js" while the page loads "admin-ui.js?v=N": two URLs, so the
        // browser ran the whole admin a second time and it looked like the page reloading.
        manualChunks(id) {
          if (id.includes("node_modules")) return "vendor";
          if (/[\\/]src[\\/](components|lib)[\\/]/.test(id) || /[\\/]pages[\\/]overview\.tsx$/.test(id)) return "shared";
          return undefined;
        },
      },
    },
  },
});
