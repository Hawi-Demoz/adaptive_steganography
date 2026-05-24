// Central API base URL for frontend. Accept either domain-only or a value ending in /api.
const rawApiBase = (import.meta.env.VITE_API_URL || 'http://localhost:5000').trim();
const noTrailingSlash = rawApiBase.replace(/\/+$/, '');
export const API_BASE = noTrailingSlash.replace(/\/api$/i, '');
