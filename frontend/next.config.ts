import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const flaskBase = process.env.FLASK_BASE_URL || "http://127.0.0.1:5000";
    return [
      {
        source: "/flask/:path*",
        destination: `${flaskBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
