import type { Monitor } from '../types'
import { StatusBadge } from './StatusBadge'
import styles from './MonitorTable.module.css'

function when(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-TW', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(value)) : '尚未檢查'
}

export function MonitorTable({ monitors }: { monitors: Monitor[] }) {
  if (!monitors.length) return <div className={styles.empty}>目前沒有符合條件的監測目標。</div>
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr><th>目標</th><th>來源</th><th>狀態</th><th>HTTP</th><th>耗時</th><th>週期</th><th>最後檢查</th></tr>
        </thead>
        <tbody>
          {monitors.map((monitor) => (
            <tr key={monitor.id}>
              <td data-label="目標">
                <strong>{monitor.name}</strong>
                <small>{monitor.source_kind === 'MOCK' ? '預期模擬情境' : monitor.source_data_date ? `資料日期 ${monitor.source_data_date}` : '外部公開 API'}</small>
              </td>
              <td data-label="來源"><span className={`${styles.source} ${styles[monitor.source_kind.toLowerCase()]}`}>{monitor.source_kind}</span></td>
              <td data-label="狀態"><StatusBadge status={monitor.latest_status} />{monitor.latest_data_warning && <small>{monitor.latest_data_warning}</small>}</td>
              <td data-label="HTTP">{monitor.latest_http_status ?? '–'}</td>
              <td data-label="耗時">{monitor.latest_latency_ms == null ? '–' : `${monitor.latest_latency_ms} ms`}</td>
              <td data-label="週期">{monitor.check_interval_minutes} 分鐘</td>
              <td data-label="最後檢查">{when(monitor.last_checked_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

