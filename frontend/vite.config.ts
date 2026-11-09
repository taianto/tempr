import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL("..", import.meta.url));
  const env = loadEnv(mode, envDir, "");
  const target = env.VITE_API_PROXY_TARGET || "http://localhost:8000";

  return {
    envDir,
    plugins: [react()],
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    server: {
      proxy: {
        "/api": { target, changeOrigin: true },
        "/docs": { target, changeOrigin: true },
        "/openapi.json": { target, changeOrigin: true },
      },
    },
  };
});
