/**
 * lib/api.ts
 * ------------
 * Thin fetch wrapper around the FastAPI backend. Client-side only —
 * this dashboard talks to the backend directly from the browser rather
 * than through Next.js server components, since every endpoint it
 * needs is already a fully-formed REST API with its own auth.
 *
 * Set NEXT_PUBLIC_API_BASE_URL in .env.local (defaults to the FastAPI
 * dev server on :8000).
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "agenthub_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export function apiBaseUrl() {
  return API_BASE_URL;
}

// ------------------------------------------------------------------ //
// Shared types for the pieces of the backend this dashboard touches
// ------------------------------------------------------------------ //

export interface Business {
  id: number;
  user_id: number;
  business_name: string;
  industry: string;
  website_url: string;

  gmail_connected: boolean;
  shopify_connected: boolean;
  shopify_store_url: string | null;
  woo_connected: boolean;
  woo_store_url: string | null;
  whatsapp_connected: boolean;
  whatsapp_business_number: string | null;
  stripe_connected: boolean;
  stripe_customer_id: string | null;
  razorpay_connected: boolean;
  jazzcash_connected: boolean;
  shiprocket_connected: boolean;
  tcs_connected: boolean;
  leopards_connected: boolean;
  sheets_connected: boolean;
  hubspot_connected: boolean;
  mailchimp_connected: boolean;
  meta_ads_connected: boolean;
}

export interface CurrentUser {
  id: number;
  name: string;
  email: string;
}
