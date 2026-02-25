import { API_BASE_URL } from "@/lib/constants";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Thin fetch wrapper that prepends the API base URL and
 * automatically parses JSON responses.
 */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      res.status,
      `API ${res.status}: ${res.statusText} — ${body}`,
    );
  }

  return res.json() as Promise<T>;
}
