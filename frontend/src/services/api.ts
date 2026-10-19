import type { CheckResult, Monitor, MonitorDraft, Overview, SessionState, SourceKind } from '../types'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

function cookie(name: string): string {
  const part = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${name}=`))
  return part ? decodeURIComponent(part.split('=').slice(1).join('=')) : ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = cookie('cloudpulse_csrf')
    if (token) headers.set('X-CSRF-Token', token)
  }
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  overview: () => request<Overview>('/api/v1/overview'),
  monitors: (includeDisabled = false) =>
    request<Monitor[]>(`/api/v1/monitors?include_disabled=${includeDisabled}`),
  checks: (source?: SourceKind, monitorId?: string) => {
    const params = new URLSearchParams({ limit: '50' })
    if (source) params.set('source_kind', source)
    if (monitorId) params.set('monitor_id', monitorId)
    return request<CheckResult[]>(`/api/v1/checks?${params}`)
  },
  session: () => request<SessionState>('/api/v1/auth/session'),
  login: (password: string) =>
    request<SessionState>('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request<void>('/api/v1/auth/logout', { method: 'POST' }),
  createMonitor: (payload: MonitorDraft & { target_key: string }) =>
    request<Monitor>('/api/v1/monitors', { method: 'POST', body: JSON.stringify(payload) }),
  updateMonitor: (id: string, payload: MonitorDraft) =>
    request<Monitor>(`/api/v1/monitors/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMonitor: (id: string) => request<void>(`/api/v1/monitors/${id}`, { method: 'DELETE' }),
}

