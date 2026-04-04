import { ApiClientError, isApiErrorPayload, type ApiErrorPayload } from "@/shared/api/errors";

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  auth?: "required" | "optional" | "none";
  body?: BodyInit | FormData | Record<string, unknown> | null;
}

export interface ApiResponse<T> {
  data: T;
  headers: Headers;
  status: number;
}

export interface ApiClient {
  request<T>(path: string, options?: ApiRequestOptions): Promise<T>;
  requestWithMeta?<T>(path: string, options?: ApiRequestOptions): Promise<ApiResponse<T>>;
  get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T>;
  post<T>(
    path: string,
    body?: ApiRequestOptions["body"],
    options?: Omit<ApiRequestOptions, "method" | "body">,
  ): Promise<T>;
}

interface CreateApiClientOptions {
  baseUrl: string;
  getAccessToken?: () => Promise<string | null>;
  onUnauthorized?: (error: ApiClientError) => Promise<void> | void;
}

function buildUrl(baseUrl: string, path: string): string {
  if (baseUrl.trim().length === 0) {
    throw new Error("Public runtime config is missing NEXT_PUBLIC_API_BASE_URL.");
  }

  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  return new URL(normalizedPath, normalizedBase).toString();
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function isPlainObjectBody(value: ApiRequestOptions["body"]): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !(value instanceof FormData);
}

export function createApiClient({
  baseUrl,
  getAccessToken,
  onUnauthorized,
}: CreateApiClientOptions): ApiClient {
  async function performRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<ApiResponse<T>> {
    const { auth = "optional", body, headers, ...rest } = options;
    const requestHeaders = new Headers(headers);

    if (auth !== "none" && getAccessToken) {
      const accessToken = await getAccessToken();
      if (accessToken) {
        requestHeaders.set("Authorization", `Bearer ${accessToken}`);
      } else if (auth === "required") {
        throw new ApiClientError(401, {
          code: "UNAUTHORIZED",
          message: "Missing access token",
        });
      }
    }

    let requestBody: BodyInit | null | undefined = body as BodyInit | null | undefined;
    if (isPlainObjectBody(body)) {
      requestHeaders.set("Content-Type", "application/json");
      requestBody = JSON.stringify(body);
    }

    const response = await fetch(buildUrl(baseUrl, path), {
      ...rest,
      body: requestBody,
      headers: requestHeaders,
    });
    const parsedBody = await parseResponseBody(response);

    if (!response.ok) {
      const payload = isApiErrorPayload(parsedBody) ? parsedBody : fallbackApiError(response, parsedBody);
      const error = new ApiClientError(response.status, payload);
      if (response.status === 401 && auth !== "none" && onUnauthorized) {
        await onUnauthorized(error);
      }
      throw error;
    }

    return {
      data: parsedBody as T,
      headers: response.headers,
      status: response.status,
    };
  }

  return {
    async request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
      const response = await performRequest<T>(path, options);
      return response.data;
    },
    requestWithMeta<T>(path: string, options: ApiRequestOptions = {}): Promise<ApiResponse<T>> {
      return performRequest<T>(path, options);
    },

    get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      return this.request<T>(path, { ...options, method: "GET" });
    },

    post<T>(
      path: string,
      body?: ApiRequestOptions["body"],
      options?: Omit<ApiRequestOptions, "method" | "body">,
    ): Promise<T> {
      return this.request<T>(path, { ...options, method: "POST", body });
    },
  };
}

function fallbackApiError(response: Response, parsedBody: unknown): ApiErrorPayload {
  if (typeof parsedBody === "string" && parsedBody.trim()) {
    return { message: parsedBody.trim() };
  }

  return {
    code: response.status >= 500 ? "UPSTREAM_ERROR" : "REQUEST_FAILED",
    message: response.statusText || `Request failed with status ${response.status}`,
  };
}
