const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const DEFAULT_TIMEOUT_MS = 30_000;

export type ApiErrorBody = {
  message?: string;
  detail?: string | Array<{ msg: string; loc?: Array<string | number> }>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: ApiErrorBody,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getAccessToken() {
  return sessionStorage.getItem("darkaudit.accessToken");
}

function errorMessage(body?: ApiErrorBody) {
  if (body?.message) return body.message;
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail)) return body.detail.map((item) => item.msg).join(", ");
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.";
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    init?.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const token = getAccessToken();
  const isFormData = init?.body instanceof FormData;

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal,
      credentials: "include",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });

    if (!response.ok) {
      const body = (await response.json().catch(() => undefined)) as ApiErrorBody | undefined;
      throw new ApiError(errorMessage(body), response.status, body);
    }

    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("요청 시간이 초과되었습니다. 다시 시도해주세요.", 408);
    }
    throw new ApiError("서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.", 0);
  } finally {
    window.clearTimeout(timeoutId);
  }
}
