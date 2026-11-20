import type { components } from './generated/types'

export type Schema = components['schemas']
export type ApiError = { status: number; code: string; detail: unknown }

const ACCESS_KEY = 'ft_access'
const REFRESH_KEY = 'ft_refresh'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function setTokens(access: string, refresh?: string | null): void {
  localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export class RequestError extends Error {
  constructor(public apiError: ApiError) {
    super(typeof apiError.detail === 'string' ? apiError.detail : apiError.code)
  }
}

async function refreshAccess(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return false
  const response = await fetch('/api/auth/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) {
    clearTokens()
    return false
  }
  const data = (await response.json()) as Schema['AuthTokens']
  setTokens(data.access, data.refresh)
  return true
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
  signal?: AbortSignal
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const doFetch = (token: string | null) => {
    const url = new URL(path, window.location.origin)
    for (const [key, value] of Object.entries(options.params ?? {})) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
    }
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (options.body !== undefined) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`
    return fetch(url, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  }

  let response = await doFetch(getAccessToken())
  if (response.status === 401 && (await refreshAccess())) {
    response = await doFetch(getAccessToken())
  }

  const payload = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const envelope = payload as { error?: ApiError } | null
    throw new RequestError(
      envelope?.error ?? { status: response.status, code: 'request_failed', detail: payload },
    )
  }
  return payload as T
}

export function errorMessage(error: unknown): string {
  if (error instanceof RequestError) {
    const detail = error.apiError.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') {
      const record = detail as Record<string, unknown>
      const first = Object.values(record)[0]
      if (Array.isArray(first)) return String(first[0])
      if (typeof first === 'string') return first
    }
    return error.message
  }
  return error instanceof Error ? error.message : 'Something went wrong'
}
