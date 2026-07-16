/** @type {import('next').NextConfig} */

// The dev server rejects cross-origin requests unless the origin is allow-listed. This repo is
// meant to be publishable, so the internal hostname is NOT hardcoded here — set it in .env:
//   NEXT_ALLOWED_DEV_ORIGINS=lawn.your-internal-host
// Comma-separated for multiple. Empty/unset is fine for pure localhost dev.
const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const nextConfig = {
  allowedDevOrigins,
};

export default nextConfig;
