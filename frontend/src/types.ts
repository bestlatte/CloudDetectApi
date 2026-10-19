export type SourceKind = 'REAL' | 'MOCK'
export type HealthStatus = 'UP' | 'DOWN' | 'DEGRADED' | 'UNKNOWN'

export interface StatusCounts {
  up: number
  down: number
  degraded: number
  unknown: number
}

export interface Overview {
  total_targets: number
  real: StatusCounts
  mock: StatusCounts
  last_job_at: string | null
}

export interface Monitor {
  id: string
  target_key: string
  name: string
  url: string
  source_kind: SourceKind
  expected_status: number
  max_latency_ms: number
  check_interval_minutes: number
  validation_profile: string
  enabled: boolean
  last_checked_at: string | null
  next_check_at: string | null
  latest_status: HealthStatus
  latest_http_status: number | null
  latest_latency_ms: number | null
  latest_reason_code: string | null
  latest_data_warning: string | null
  source_data_date: string | null
}

export interface CheckResult {
  id: string
  monitor_id: string
  monitor_name: string
  source_kind: SourceKind
  checked_at: string
  status: Exclude<HealthStatus, 'UNKNOWN'>
  http_status: number | null
  latency_ms: number | null
  reason_code: string | null
  error_summary: string | null
  source_data_date: string | null
  data_warning: string | null
  execution_id: string
}

export interface SessionState {
  authenticated: boolean
  expires_at: string | null
}

export interface MonitorDraft {
  name?: string
  expected_status?: number
  max_latency_ms?: number
  check_interval_minutes?: number
  enabled?: boolean
}

