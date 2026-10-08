// Production uses the Vercel /api proxy so auth cookies stay same-origin.
export const API_BASE = (import.meta.env.PROD ? '' : (import.meta.env.VITE_API_URL || 'http://localhost:5000')).replace(/\/+$/, '');
