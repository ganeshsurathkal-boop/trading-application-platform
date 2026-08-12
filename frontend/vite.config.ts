import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
// HTTPS is required for Zerodha Kite Connect OAuth redirect (https://localhost:5173)
export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    https: {},
    port: 5173,
  },
})
