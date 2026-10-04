import path from "node:path"
import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Turbopack resolves dev output from the repository root (which also holds the Python
  // backend); without this it writes static media to frontend/frontend/.next.
  turbopack: { root: path.resolve(__dirname, "..") },
}

export default nextConfig
