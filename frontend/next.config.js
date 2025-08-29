/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    unoptimized: true
  },
  trailingSlash: true,
  assetPrefix: '.',
};

module.exports = nextConfig;
