/**
 * API Client - fetch wrapper with Telegram WebApp authentication
 */


// =============================================================================
// Configuration
// =============================================================================

const API_URL = import.meta.env.VITE_API_URL || "/api";
const MOCK_INIT_DATA = import.meta.env.VITE_MOCK_INIT_DATA || "";

// =============================================================================
// Auth Helper
// =============================================================================

/**
 * Get Telegram initData for API authorization.
 * Uses real initData from WebApp or mock data in development.
 */
function getInitData(): string {
  // Try to get real initData from Telegram WebApp
  if (
    typeof window !== "undefined" &&
    window.Telegram?.WebApp?.initData
  ) {
    return window.Telegram.WebApp.initData;
  }

  // Fallback to mock data in development
  if (MOCK_INIT_DATA) {
    return MOCK_INIT_DATA;
  }

  return "";
}

// =============================================================================
// Error Classes
// =============================================================================

export class APIClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = "APIClientError";
  }
}

export class InsufficientCreditsAPIError extends APIClientError {
  constructor(
    public balance: number,
    public required: number
  ) {
    super("Insufficient credits", 400, { balance, required });
    this.name = "InsufficientCreditsAPIError";
  }
}

export class UnauthorizedError extends APIClientError {
  constructor() {
    super("Unauthorized", 401);
    this.name = "UnauthorizedError";
  }
}

// =============================================================================
// API Client Class
// =============================================================================

type RequestMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

interface RequestOptions {
  method?: RequestMethod;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Build URL with query parameters
   */
  private buildUrl(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>
  ): string {
    // Handle relative base URLs (like "/api")
    const fullUrl = this.baseUrl.startsWith("http")
      ? `${this.baseUrl}${endpoint}`
      : `${window.location.origin}${this.baseUrl}${endpoint}`;

    const url = new URL(fullUrl);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  /**
   * Make an authenticated API request
   */
  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, params } = options;

    const initData = getInitData();
    if (!initData) {
      throw new UnauthorizedError();
    }

    const url = this.buildUrl(endpoint, params);

    const headers: Record<string, string> = {
      Authorization: `tma ${initData}`,
    };

    if (body) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    // Handle non-OK responses
    if (!response.ok) {
      const errorData = (await response.json().catch(() => ({}))) as Record<
        string,
        unknown
      >;

      // Handle insufficient credits error
      if (
        response.status === 400 &&
        typeof errorData.detail === "object" &&
        errorData.detail !== null
      ) {
        const detail = errorData.detail as Record<string, unknown>;
        if (
          detail.detail === "Insufficient credits" &&
          typeof detail.balance === "number" &&
          typeof detail.required === "number"
        ) {
          throw new InsufficientCreditsAPIError(detail.balance, detail.required);
        }
      }

      // Handle unauthorized
      if (response.status === 401) {
        throw new UnauthorizedError();
      }

      // Generic error
      const message =
        typeof errorData.detail === "string"
          ? errorData.detail
          : "Request failed";

      throw new APIClientError(message, response.status, errorData);
    }

    return response.json() as Promise<T>;
  }

  /**
   * GET request
   */
  get<T>(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>
  ): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", params });
  }

  /**
   * POST request
   */
  post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "POST", body });
  }
}

// =============================================================================
// Export singleton instance
// =============================================================================

export const apiClient = new APIClient(API_URL);
