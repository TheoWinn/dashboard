import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// adjust if needed: this assumes vite.config.js is in repo-root/Frontend/
const envDir = path.resolve(__dirname, "..");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, "");

  const allowedHosts = env.VITE_ALLOWED_HOSTS
    ? env.VITE_ALLOWED_HOSTS.split(",").map((h) => h.trim()).filter(Boolean)
    : ["localhost", "127.0.0.1"];

  return {
    plugins: [react()],
    base: "./",

    // IMPORTANT: make Vite read env from repo-root (or wherever your .env lives)
    envDir,

    server: {
      allowedHosts,
    },

    preview: {
      host: true,
      allowedHosts,
    },
  };
});
