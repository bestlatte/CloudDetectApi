import type { HealthStatus } from '../types'
import styles from './StatusBadge.module.css'

export function StatusBadge({ status }: { status: HealthStatus }) {
  return <span className={`${styles.badge} ${styles[status.toLowerCase()]}`}>{status}</span>
}

