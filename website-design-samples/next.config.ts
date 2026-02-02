import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Disable Turbopack for compatibility */
  experimental: {
    // Use webpack instead of turbopack for build
  },
};

export default nextConfig;
