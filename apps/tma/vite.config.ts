import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "")

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      allowedHosts: [".ngrok-free.app", ".ngrok-free.dev"],
      proxy: {
        "/api": {
          target: env.VITE_DEV_API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        "@": "/src",
      },
    },
  }
})
