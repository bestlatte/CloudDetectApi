import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders text in addition to color', () => {
    render(<StatusBadge status="DOWN" />)
    expect(screen.getByText('DOWN')).toBeVisible()
  })
})

