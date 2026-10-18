// Production uses the same HTTPS origin as FastAPI. Override only for a separate API host.
export function serverBaseUrl(configuredOrigin?: string): string {
  return (configuredOrigin ?? "").replace(/\/$/, "");
}

export const SERVER_BASE_URL = serverBaseUrl(import.meta.env?.VITE_API_ORIGIN);
export const API_BASE_URL = `${SERVER_BASE_URL}/api`;
