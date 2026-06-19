/** Response-envelope shapes returned by the Django backend (snake_case). */

export interface Meta {
  request_id: string | null;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
}

export interface ApiEnvelope<T> {
  data: T;
  meta?: Meta;
}

export interface ApiListEnvelope<T> {
  data: T[];
  pagination: Pagination;
  meta?: Meta;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
  meta?: Meta;
}

/** Normalized paginated result used across query hooks. */
export interface Paginated<T> {
  items: T[];
  pagination: Pagination;
}

/** Thrown by the API client on any non-2xx response. `code` mirrors the backend. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(opts: {
    code: string;
    message: string;
    status: number;
    details?: Record<string, unknown>;
  }) {
    super(opts.message);
    this.name = "ApiError";
    this.code = opts.code;
    this.status = opts.status;
    this.details = opts.details ?? {};
  }

  /** First field-level validation message, if the backend sent `details`. */
  get firstFieldError(): string | null {
    for (const value of Object.values(this.details)) {
      if (Array.isArray(value) && value.length && typeof value[0] === "string") {
        return value[0];
      }
      if (typeof value === "string") return value;
    }
    return null;
  }
}
