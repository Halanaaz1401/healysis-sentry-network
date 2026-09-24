import { API_BASE_URL, getApiBaseUrl, UserIdentity, MOCK_USERS } from "@/config";

export interface ApiOptions extends RequestInit {
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T = any>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  let token = "";
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("healysis_user");
    if (saved) {
      try {
        const u: UserIdentity = JSON.parse(saved);
        if (u && u.token) {
          token = u.token;
        }
      } catch {
        // fallback
      }
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": token.startsWith("Bearer ") ? token : `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const baseUrl = getApiBaseUrl();
  const url = endpoint.startsWith("http") ? endpoint : `${baseUrl}${cleanEndpoint}`;

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = "";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.error || response.statusText;
    } catch {
      errorDetail = response.statusText;
    }

    if (response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("healysis_user");
        if (window.location.pathname !== "/login") {
          window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
        }
      }
      throw new ApiError(401, errorDetail || "Your session could not be authenticated. Please sign in again.");
    } else if (response.status === 403) {
      throw new ApiError(403, errorDetail || "You are authenticated but do not have permission to perform this action.");
    } else if (response.status === 404) {
      throw new ApiError(404, errorDetail || "The requested facility/resource was not found.");
    } else {
      throw new ApiError(response.status, errorDetail || "The server encountered an unexpected error.");
    }
  }

  return response.json();
}
