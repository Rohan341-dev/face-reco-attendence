import AsyncStorage from "@react-native-async-storage/async-storage"

import type { components } from "./api/generated/types"

export type Schema = components["schemas"]
export type QueuedEvent = Schema["AttendanceEventInput"]

const ACCESS_KEY = "ft_access"
const REFRESH_KEY = "ft_refresh"
const QUEUE_KEY = "ft_offline_queue"

const BASE_URL = "http://localhost:8000"

export async function getAccess(): Promise<string | null> {
  return AsyncStorage.getItem(ACCESS_KEY)
}

export async function saveTokens(access: string, refresh?: string | null): Promise<void> {
  await AsyncStorage.setItem(ACCESS_KEY, access)
  if (refresh) await AsyncStorage.setItem(REFRESH_KEY, refresh)
}

export async function clearTokens(): Promise<void> {
  await AsyncStorage.multiRemove([ACCESS_KEY, REFRESH_KEY])
}

export async function getQueue(): Promise<QueuedEvent[]> {
  const raw = await AsyncStorage.getItem(QUEUE_KEY)
  try {
    return raw ? (JSON.parse(raw) as QueuedEvent[]) : []
  } catch {
    return []
  }
}

export async function saveQueue(events: QueuedEvent[]): Promise<void> {
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(events))
}

async function refresh(): Promise<boolean> {
  const token = await AsyncStorage.getItem(REFRESH_KEY)
  if (!token) return false
  const response = await fetch(`${BASE_URL}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: token }),
  })
  if (!response.ok) {
    await clearTokens()
    return false
  }
  const data = (await response.json()) as Schema["AuthTokens"]
  await saveTokens(data.access, data.refresh)
  return true
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" }
  if (options.body) headers["Content-Type"] = "application/json"
  const access = await getAccess()
  if (access) headers.Authorization = `Bearer ${access}`

  let response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (response.status === 401 && (await refresh())) {
    const renewed = await getAccess()
    if (renewed) headers.Authorization = `Bearer ${renewed}`
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const envelope = payload as { error?: { detail?: unknown } } | null
    const detail = envelope?.error?.detail
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`)
  }
  return payload as T
}

export const api = {
  login: (email: string, password: string) =>
    request<Schema["AuthTokens"] | { mfa_required: boolean; mfa_token: string }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<Schema["User"]>("/api/auth/me/"),
  records: () => request<Schema["AttendanceRecord"][]>("/api/attendance/records/"),
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
