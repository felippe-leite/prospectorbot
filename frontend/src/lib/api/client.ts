// Thin fetch wrapper: every backend call goes through `request`.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "")

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = "ApiError"
  }

  /** True when the API could not be reached at all. */
  get offline() {
    return this.status === 0
  }
}

type Query = Record<string, string | number | undefined | (string | number)[]>

export function withQuery(path: string, query: Query = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item !== undefined && item !== "") params.append(key, String(item))
    }
  }
  const search = params.toString()
  return search ? `${path}?${search}` : path
}

function errorMessage(body: unknown, status: number): string {
  // FastAPI returns {detail: string} or {detail: [{msg, loc}]} for validation errors.
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item: { msg?: string }) => (item.msg ?? "Invalid value").replace(/^Value error, /, "")).join("; ")
  }
  return `Request failed (HTTP ${status}).`
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
    })
  } catch {
    throw new ApiError("Unable to connect to ProspectorBot API.", 0)
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(errorMessage(body, response.status), response.status)
  return body as T
}
