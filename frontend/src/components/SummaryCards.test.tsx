import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SummaryCards } from './SummaryCards'

describe('SummaryCards', () => {
  it('keeps real service counts independent from mock failures', () => {
    render(<SummaryCards overview={{ total_targets: 8, real: { up: 4, down: 0, degraded: 0, unknown: 0 }, mock: { up: 1, down: 2, degraded: 1, unknown: 0 }, last_job_at: null }} />)
    expect(screen.getByText('真實 API 異常').parentElement).toHaveTextContent('0')
  })
})
