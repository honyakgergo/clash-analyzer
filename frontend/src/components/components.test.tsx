import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { TagSearch } from './Layout'
import { GameCard, InsightList, Segmented, WinRateBar } from './ui'

describe('TagSearch', () => {
  function setup() {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<TagSearch />} />
          <Route path="/player/:tag" element={<p>player page</p>} />
        </Routes>
      </MemoryRouter>,
    )
    return screen.getByLabelText('Player tag')
  }

  it('navigates to the normalized tag', () => {
    const input = setup()
    fireEvent.change(input, { target: { value: '#pqggvojp' } })
    fireEvent.submit(input.closest('form')!)
    expect(screen.getByText('player page')).toBeInTheDocument()
  })

  it('shows an error for invalid tags', () => {
    const input = setup()
    fireEvent.change(input, { target: { value: 'hello' } })
    fireEvent.submit(input.closest('form')!)
    expect(screen.getByText(/Tags use only/)).toBeInTheDocument()
  })
})

describe('ui', () => {
  it('WinRateBar shows the rate or a dash with no games', () => {
    const { rerender } = render(<WinRateBar rate={{ win_rate: 62.5, games: 8, ci_low: 30, ci_high: 86 }} />)
    expect(screen.getByText('63%')).toBeInTheDocument()
    rerender(<WinRateBar rate={{ win_rate: null, games: 0 }} />)
    expect(screen.getByText('–')).toBeInTheDocument()
  })

  it('GameCard shows level and form', () => {
    render(<GameCard card={{ id: 1, name: 'Hog Rider', rarity: 'rare', elixir: 4, form: 'evo', icon: null, level: 15 }} />)
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('evo')).toBeInTheDocument()
  })

  it('InsightList labels each insight level', () => {
    render(<InsightList items={[{ level: 'warn', text: 'Tilt alert' }, { level: 'good', text: 'Nice' }]} />)
    expect(screen.getByLabelText('warn')).toBeInTheDocument()
    expect(screen.getByText('Tilt alert')).toBeInTheDocument()
  })

  it('Segmented marks the selected option and reports changes', () => {
    let value = 'a'
    render(<Segmented label="x" value={value} onChange={(v) => (value = v)} options={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]} />)
    expect(screen.getByRole('radio', { name: 'A' })).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(screen.getByRole('radio', { name: 'B' }))
    expect(value).toBe('b')
  })
})

describe('theme toggle', () => {
  it('switches between exactly two modes and persists the choice', async () => {
    const { default: Layout } = await import('./Layout')
    localStorage.setItem('theme', 'dark')
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    )
    const button = screen.getByRole('button', { name: 'Switch to light mode' })
    expect(document.documentElement.dataset.theme).toBe('dark')
    fireEvent.click(button)
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('theme')).toBe('light')
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('ignores the old "system" value and falls back to a real mode', async () => {
    const { initialTheme } = await import('../lib/theme')
    localStorage.setItem('theme', 'system')
    expect(['light', 'dark']).toContain(initialTheme())
  })
})
