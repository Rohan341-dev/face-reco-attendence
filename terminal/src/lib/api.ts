import type { components } from "./api/generated/types"

export type Schema = components["schemas"]

const TOKEN_KEY = "ft_device_token"
const QUEUE_KEY = "ft_offline_queue"

export type QueuedEvent = Schema["AttendanceEventInput"]

export function getDeviceToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setDeviceToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearDeviceToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getQueue(): QueuedEvent[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]") as QueuedEvent[]
  } catch {
    return []
  }
}

export function setQueue(events: QueuedEvent[]): void {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(events))
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" }
  if (options.body) headers["Content-Type"] = "application/json"
  if (authenticated) {
    const token = getDeviceToken()
    if (token) headers.Authorization = `Device ${token}`
  }
  const response = await fetch(path, { ...options, headers })
  const payload = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const envelope = payload as { error?: { detail?: unknown } } | null
    const detail = envelope?.error?.detail
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`)
  }
  return payload as T
}

export const api = {
  auth: (token: string) =>
    request<{ access: string; device_id: string; organization_id: string }>(
      "/api/devices/auth/",
      { method: "POST", body: JSON.stringify({ token }) },
      false,
    ),
  current: () => request<Schema["Device"]>("/api/devices/current/"),
  people: () => request<Schema["Person"][]>("/api/people/"),
  event: (body: QueuedEvent) =>
    request<Schema["AttendanceEvent"]>("/api/attendance/events/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  sync: (events: QueuedEvent[]) =>
    request<{ results: Array<{ idempotency_key: string; status: string }> }>("/api/attendance/sync/", {
      method: "POST",
      body: JSON.stringify({ events }),
    }),
}
