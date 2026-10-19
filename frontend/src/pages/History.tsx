import { useCallback, useEffect, useState } from 'react'
import { StatusBadge } from '../components/StatusBadge'
import { api } from '../services/api'
import type { CheckResult, Monitor, SourceKind } from '../types'
import styles from './Pages.module.css'

export function History() {
  const [checks, setChecks] = useState<CheckResult[]>([])
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [source, setSource] = useState<SourceKind | ''>('')
  const [monitorId, setMonitorId] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    try { const [nextChecks, nextMonitors] = await Promise.all([api.checks(source || undefined, monitorId || undefined), api.monitors()]); setChecks(nextChecks); setMonitors(nextMonitors); setError('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : '無法載入歷史紀錄。') }
    finally { setLoading(false) }
  }, [monitorId, source])
  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(timer)
  }, [load])
  if (loading) return <div className={styles.state}>正在載入檢查歷史…</div>
  return (
    <div className={styles.stack}>
      <header><p className={styles.eyebrow}>AUDIT TRAIL</p><h1>檢查歷史</h1><p className={styles.lead}>最近 50 筆實際檢查結果；不保存完整第三方回應本文。</p></header>
      <div className={styles.filters}><select value={source} onChange={(event) => setSource(event.target.value as SourceKind | '')}><option value="">全部來源</option><option value="REAL">REAL</option><option value="MOCK">MOCK</option></select><select value={monitorId} onChange={(event) => setMonitorId(event.target.value)}><option value="">全部目標</option>{monitors.map((monitor) => <option key={monitor.id} value={monitor.id}>{monitor.name}</option>)}</select></div>
      {error ? <div className={`${styles.state} ${styles.error}`}>{error}</div> : <div className={styles.tableWrap}><table><thead><tr><th>檢查時間</th><th>目標</th><th>來源</th><th>結果</th><th>HTTP</th><th>耗時</th><th>原因／資料日期</th></tr></thead><tbody>{checks.map((check) => <tr key={check.id}><td>{new Date(check.checked_at).toLocaleString('zh-TW')}</td><td>{check.monitor_name}</td><td>{check.source_kind}</td><td><StatusBadge status={check.status} /></td><td>{check.http_status ?? '—'}</td><td>{check.latency_ms == null ? '—' : `${check.latency_ms} ms`}</td><td>{check.reason_code ?? check.data_warning ?? '—'}{check.source_data_date && <small>資料日 {check.source_data_date}</small>}</td></tr>)}</tbody></table>{!checks.length && <div className={styles.state}>尚無檢查紀錄。</div>}</div>}
    </div>
  )
}

