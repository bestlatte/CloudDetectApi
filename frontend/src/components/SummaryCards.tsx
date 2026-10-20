import type { Overview } from '../types'
import styles from './SummaryCards.module.css'

interface SummaryCardsProps {
  overview: Overview
}

export function SummaryCards({ overview }: SummaryCardsProps) {
  const realTotal = overview.real.up + overview.real.down + overview.real.degraded + overview.real.unknown
  const mockTotal = overview.mock.up + overview.mock.down + overview.mock.degraded + overview.mock.unknown
  const cards = [
    { label: '真實 API 正常', value: overview.real.up, tone: 'healthy' },
    { label: '真實 API 異常', value: overview.real.down, tone: 'danger' },
    { label: '真實 API 降級', value: overview.real.degraded, tone: 'warning' },
    { label: '尚無結果', value: overview.real.unknown, tone: 'neutral' },
  ]
  return (
    <section className={styles.summary} aria-label="REAL 與 MOCK 監測摘要">
      <div className={styles.summaryHead}>
        <div><span>正式服務</span><strong>{realTotal} 個 REAL 目標</strong></div>
        <small>共 {overview.total_targets} 個監測目標</small>
      </div>
      <div className={styles.metrics}>
        {cards.map((card) => (
          <article className={`${styles.metric} ${styles[card.tone]}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
      <div className={styles.mockBand}>
        <div><span>模擬情境</span><strong>{mockTotal} 個 MOCK 目標</strong></div>
        <dl><div><dt>正常</dt><dd>{overview.mock.up}</dd></div><div><dt>異常</dt><dd>{overview.mock.down}</dd></div><div><dt>降級</dt><dd>{overview.mock.degraded}</dd></div><div><dt>未知</dt><dd>{overview.mock.unknown}</dd></div></dl>
      </div>
    </section>
  )
}

