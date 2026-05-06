const DEFAULT_API_BASE_URL = "http://lawn-api:8000";

export type ApiMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;
}

type RequestOptions<TBody> = {
  method?: ApiMethod;
  body?: TBody;
  headers?: HeadersInit;
  cache?: RequestCache;
  next?: NextFetchRequestConfig;
};

export async function apiRequest<TResponse, TBody = unknown>(
  path: string,
  options: RequestOptions<TBody> = {},
): Promise<TResponse> {
  const { method = "GET", body, headers, cache = "no-store", next } = options;

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache,
    next,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(`API request failed: ${method} ${path}`, response.status, payload);
  }

  return payload as TResponse;
}

export async function getHealth() {
  return apiRequest<{ status: string; db?: string }>("/health", { method: "GET" });
}