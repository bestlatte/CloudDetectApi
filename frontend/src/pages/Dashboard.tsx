import { useCallback, useEffect, useMemo, useState } from 'react'
import { MonitorTable } from '../components/MonitorTable'
import { SummaryCards } from '../components/SummaryCards'
import { api } from '../services/api'
import type { Monitor, Overview } from '../types'
import styles from './Pages.module.css'

type Filter = 'ALL' | 'REAL' | 'MOCK' | 'ISSUES'

export function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [filter, setFilter] = useState<Filter>('ALL')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [nextOverview, nextMonitors] = await Promise.all([api.overview(), api.monitors()])
      setOverview(nextOverview)
      setMonitors(nextMonitors)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '無法載入監測資料。')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(timer)
  }, [load])

  const visible = useMemo(() => monitors.filter((monitor) => {
    if (filter === 'REAL' || filter === 'MOCK') return monitor.source_kind === filter
    if (filter === 'ISSUES') return ['DOWN', 'DEGRADED'].includes(monitor.latest_status)
    return true
  }), [filter, monitors])

  if (loading) return <div className={styles.state}>正在同步監測資料…</div>
  if (error) return <div className={`${styles.state} ${styles.error}`}>{error}<button onClick={() => void load()}>重試</button></div>
  if (!overview) return <div className={styles.state}>尚無摘要資料。</div>

  return (
    <div className={styles.stack}>
      <header className={styles.hero}>
        <div><p className={styles.eyebrow}>OPERATIONS / LIVE VIEW</p><h1>API 健康狀態</h1><p>真實服務與受控故障情境分流呈現，不把模擬異常計入正式可用率。</p></div>
        <div className={styles.sync}><span aria-hidden="true" />上次排程<br /><strong>{overview.last_job_at ? new Date(overview.last_job_at).toLocaleString('zh-TW') : '尚未執行'}</strong></div>
      </header>
      <SummaryCards overview={overview} />
      <section>
        <div className={styles.sectionHead}><div><p className={styles.eyebrow}>TARGETS</p><h2>監測目標</h2></div><div className={styles.filters}>
          {(['ALL', 'REAL', 'MOCK', 'ISSUES'] as const).map((item) => <button className={filter === item ? styles.active : ''} key={item} onClick={() => setFilter(item)}>{item === 'ALL' ? '全部' : item === 'ISSUES' ? '異常' : item}</button>)}
        </div></div>
        <MonitorTable monitors={visible} />
      </section>
    </div>
  )
}

