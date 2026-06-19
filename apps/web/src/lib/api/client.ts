import { useAuthStore } from "@/lib/auth/store";
import {
  ApiError,
  type ApiEnvelope,
  type ApiListEnvelope,
  type Paginated,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type QueryParams = Record<
  string,
  string | number | boolean | null | undefined
>;

interface RequestOptions {
  query?: QueryParams;
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Set false for login/refresh so we don't attach (or refresh) a token. */
  auth?: boolean;
  /** internal: prevents infinite refresh loops */
  _retried?: boolean;
}

function buildUrl(path: string, query?: QueryParams): string {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(buildUrl("/api/v1/auth/refresh/"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ refresh: refreshToken }),
        });
        if (!res.ok) return null;
        const json = (await res.json()) as ApiEnvelope<{
          access: string;
          refresh?: string;
        }>;
        const access = json?.data?.access ?? null;
        if (access) {
          useAuthStore.getState().setTokens({
            access,
            refresh: json.data.refresh ?? null,
          });
        }
        return access;
      } catch {
        return null;
      }
    })();
    void refreshPromise.finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function rawRequest(
  method: string,
  path: string,
  opts: RequestOptions,
): Promise<Response> {
  const { accessToken, organizationId } = useAuthStore.getState();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers ?? {}),
  };
  if (opts.auth !== false && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (opts.auth !== false && organizationId) {
    headers["X-Organization-ID"] = organizationId;
  }

  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData; // browser sets multipart boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  return fetch(buildUrl(path, opts.query), {
    method,
    headers,
    body,
    signal: opts.signal,
    cache: "no-store",
  });
}

async function execute(
  method: string,
  path: string,
  opts: RequestOptions,
): Promise<Response> {
  let res = await rawRequest(method, path, opts);

  if (res.status === 401 && opts.auth !== false && !opts._retried) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      res = await rawRequest(method, path, { ...opts, _retried: true });
    } else {
      useAuthStore.getState().clear();
    }
  }

  if (
    res.status === 403 &&
    opts.auth !== false &&
    !opts._retried &&
    path === "/api/v1/auth/me/" &&
    useAuthStore.getState().organizationId
  ) {
    useAuthStore.getState().clearOrganization();
    res = await rawRequest(method, path, { ...opts, _retried: true });
  }

  return res;
}

async function parseOrThrow<T>(res: Response): Promise<T> {
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = (json as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error;
    throw new ApiError({
      code: err?.code ?? "server_error",
      message: err?.message ?? res.statusText ?? "Error inesperado",
      status: res.status,
      details: err?.details ?? {},
    });
  }
  return json as T;
}

/** GET a single resource (unwraps `{ data }`). */
export async function apiGet<T>(
  path: string,
  query?: QueryParams,
  opts?: Partial<RequestOptions>,
): Promise<T> {
  const res = await execute("GET", path, { ...opts, query });
  const json = await parseOrThrow<ApiEnvelope<T>>(res);
  return json.data;
}

/** GET a paginated list (unwraps `{ data, pagination }`). */
export async function apiGetList<T>(
  path: string,
  query?: QueryParams,
  opts?: Partial<RequestOptions>,
): Promise<Paginated<T>> {
  const res = await execute("GET", path, { ...opts, query });
  const json = await parseOrThrow<ApiListEnvelope<T>>(res);
  return { items: json.data, pagination: json.pagination };
}

/** GET a non-paginated list endpoint (returns the raw `data` array). */
export async function apiGetArray<T>(
  path: string,
  query?: QueryParams,
  opts?: Partial<RequestOptions>,
): Promise<T[]> {
  return apiGet<T[]>(path, query, opts);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  opts?: Partial<RequestOptions>,
): Promise<T> {
  const res = await execute("POST", path, { ...opts, body });
  const json = await parseOrThrow<ApiEnvelope<T>>(res);
  return json.data;
}

export async function apiPatch<T>(
  path: string,
  body?: unknown,
  opts?: Partial<RequestOptions>,
): Promise<T> {
  const res = await execute("PATCH", path, { ...opts, body });
  const json = await parseOrThrow<ApiEnvelope<T>>(res);
  return json.data;
}

export async function apiDelete<T>(
  path: string,
  opts?: Partial<RequestOptions>,
): Promise<T> {
  const res = await execute("DELETE", path, { ...opts });
  const json = await parseOrThrow<ApiEnvelope<T>>(res);
  return json.data;
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  opts?: Partial<RequestOptions>,
): Promise<T> {
  const res = await execute("POST", path, { ...opts, formData });
  const json = await parseOrThrow<ApiEnvelope<T>>(res);
  return json.data;
}
