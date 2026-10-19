import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { StatusBadge } from '../components/StatusBadge'
import { ApiError, api } from '../services/api'
import type { Monitor, MonitorDraft, SessionState } from '../types'
import styles from './Pages.module.css'

const templates = [
  ['FRANKFURTER_USD_TWD', 'Frankfurter USD/TWD'],
  ['GITHUB_RATE_LIMIT', 'GitHub REST API'],
  ['OPEN_METEO_TAIPEI', 'Open-Meteo Taipei'],
  ['POKEAPI_PIKACHU', 'PokéAPI Pikachu'],
  ['MOCK_HEALTHY', 'Mock Healthy API'],
  ['MOCK_SERVER_ERROR', 'Mock Server Error'],
  ['MOCK_SLOW', 'Mock Slow API'],
  ['MOCK_BUSINESS_ERROR', 'Mock Business Error'],
] as const

function Editor({ monitor, onChanged }: { monitor: Monitor; onChanged: () => Promise<void> }) {
  const [draft, setDraft] = useState<MonitorDraft>({
    name: monitor.name,
    expected_status: monitor.expected_status,
    max_latency_ms: monitor.max_latency_ms,
    check_interval_minutes: monitor.check_interval_minutes,
    enabled: monitor.enabled,
  })
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    try { await api.updateMonitor(monitor.id, draft); await onChanged() } finally { setBusy(false) }
  }
  async function remove() {
    if (!window.confirm(`停用並移除「${monitor.name}」？歷史紀錄仍會保留。`)) return
    setBusy(true)
    try { await api.deleteMonitor(monitor.id); await onChanged() } finally { setBusy(false) }
  }
  return (
    <article className={styles.editor}>
      <div className={styles.editorTop}><div><span className={styles.kind}>{monitor.source_kind}</span><StatusBadge status={monitor.latest_status} /></div><code>{monitor.target_key}</code></div>
      <label>顯示名稱<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
      <label>核准 URL<input value={monitor.url} disabled /></label>
      <div className={styles.formGrid}>
        <label>預期 HTTP<input type="number" value={draft.expected_status} onChange={(event) => setDraft({ ...draft, expected_status: Number(event.target.value) })} /></label>
        <label>延遲門檻（ms）<input type="number" value={draft.max_latency_ms} onChange={(event) => setDraft({ ...draft, max_latency_ms: Number(event.target.value) })} /></label>
        <label>檢查週期（分鐘）<input type="number" value={draft.check_interval_minutes} onChange={(event) => setDraft({ ...draft, check_interval_minutes: Number(event.target.value) })} /></label>
      </div>
      <label className={styles.check}><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />啟用監測</label>
      <div className={styles.actions}><button disabled={busy} onClick={() => void save()}>儲存變更</button><button className={styles.dangerButton} disabled={busy} onClick={() => void remove()}>移除</button></div>
    </article>
  )
}

export function Monitors() {
  const [session, setSession] = useState<SessionState>({ authenticated: false, expires_at: null })
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [password, setPassword] = useState('')
  const [targetKey, setTargetKey] = useState<string>(templates[0][0])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    const [nextSession, nextMonitors] = await Promise.all([api.session(), api.monitors(true)])
    setSession(nextSession); setMonitors(nextMonitors)
  }, [])
  useEffect(() => {
    const refresh = () => void load().catch((error: Error) => setMessage(error.message)).finally(() => setLoading(false))
    refresh()
    const timer = window.setInterval(refresh, 60_000)
    return () => window.clearInterval(timer)
  }, [load])

  async function login(event: FormEvent) {
    event.preventDefault(); setMessage('')
    try { await api.login(password); setPassword(''); await load() } catch (error) { setMessage(error instanceof Error ? error.message : '登入失敗。') }
  }
  async function create(event: FormEvent) {
    event.preventDefault(); setMessage('')
    try { await api.createMonitor({ target_key: targetKey }); await load(); setMessage('監測目標已建立。') } catch (error) { setMessage(error instanceof ApiError ? error.message : '建立失敗。') }
  }

  if (loading) return <div className={styles.state}>正在確認管理員狀態…</div>

  if (!session.authenticated) return (
    <div className={styles.narrow}><p className={styles.eyebrow}>ADMIN ACCESS</p><h1>監測設定</h1><p className={styles.lead}>公開環境只提供讀取。登入管理員後才能修改核准的八個監測模板。</p>
      <form className={styles.login} onSubmit={login}><label>管理員密碼<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><button>登入</button>{message && <p className={styles.notice}>{message}</p>}</form>
    </div>
  )

  return (
    <div className={styles.stack}>
      <header className={styles.sectionHead}><div><p className={styles.eyebrow}>APPROVED TARGETS</p><h1>監測設定</h1></div><button className={styles.quietButton} onClick={() => void api.logout().then(load)}>登出</button></header>
      <form className={styles.createBar} onSubmit={create}><label>由核准模板新增<select value={targetKey} onChange={(event) => setTargetKey(event.target.value)}>{templates.map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label><button>新增／還原</button></form>
      {message && <p className={styles.notice}>{message}</p>}
      <section className={styles.editorGrid}>{monitors.map((monitor) => <Editor key={monitor.id} monitor={monitor} onChanged={load} />)}{!monitors.length && <div className={styles.state}>尚無監測目標，請由核准模板新增。</div>}</section>
    </div>
  )
}

