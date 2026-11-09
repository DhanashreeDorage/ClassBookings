/** @type {import('next').NextConfig} */
const nextConfig = {
  // On Render's single-container deployment, keep the local API proxy.
  // On Vercel, set NEXT_PUBLIC_API_URL to the public FastAPI backend URL;
  // the browser then calls that backend directly and this rewrite is unused.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_URL) return [];
    return [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' }];
  },
};
export default nextConfig;
