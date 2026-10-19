import type { Overview } from '../types'
import styles from './SummaryCards.module.css'

interface SummaryCardsProps {
  overview: Overview
}

export function SummaryCards({ overview }: SummaryCardsProps) {
  const cards = [
    { label: '全部監測目標', value: overview.total_targets, tone: 'neutral' },
    { label: '真實 API 正常', value: overview.real.up, tone: 'healthy' },
    { label: '真實 API 異常', value: overview.real.down, tone: 'danger' },
    { label: '真實 API 降級', value: overview.real.degraded, tone: 'warning' },
  ]
  return (
    <section className={styles.grid} aria-label="監測摘要">
      {cards.map((card) => (
        <article className={`${styles.card} ${styles[card.tone]}`} key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
    </section>
  )
}

