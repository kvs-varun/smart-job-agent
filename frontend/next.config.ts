import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const flaskBase = process.env.FLASK_BASE_URL || "http://127.0.0.1:5000";
    const v2Base = process.env.V2_API_URL || "http://127.0.0.1:8000";
    return [
      // V2 FastAPI (8-agent LangGraph backend)
      {
        source: "/api/v2/:path*",
        destination: `${v2Base}/v2/:path*`,
      },
      // V1 Flask (legacy — kept during migration)
      {
        source: "/flask/:path*",
        destination: `${flaskBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
