import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Set workspace root to prevent Turbopack from scanning parent .venv symlinks
  turbopack: {
    root: __dirname,
  },
  // Optimize images
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
