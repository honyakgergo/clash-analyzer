import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { ApiError } from './api/client'
import Layout from './components/Layout'
import { Loading } from './components/ui'
const ClanPage = lazy(() => import('./pages/ClanPage'))
const HomePage = lazy(() => import('./pages/HomePage'))
const MetaPage = lazy(() => import('./pages/MetaPage'))
const BattlesTab = lazy(() => import('./pages/player/BattlesTab'))
const MasteryTab = lazy(() => import('./pages/player/MasteryTab'))
const MetaTab = lazy(() => import('./pages/player/MetaTab'))
const OverviewTab = lazy(() => import('./pages/player/OverviewTab'))
const PlayerLayout = lazy(() => import('./pages/player/PlayerLayout'))
const ProgressTab = lazy(() => import('./pages/player/ProgressTab'))
const UpgradesTab = lazy(() => import('./pages/player/UpgradesTab'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<Loading />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="meta" element={<MetaPage />} />
            <Route path="clan/:tag" element={<ClanPage />} />
            <Route path="player/:tag" element={<PlayerLayout />}>
              <Route index element={<OverviewTab />} />
              <Route path="battles" element={<BattlesTab />} />
              <Route path="progress" element={<ProgressTab />} />
              <Route path="upgrades" element={<UpgradesTab />} />
              <Route path="mastery" element={<MasteryTab />} />
              <Route path="meta" element={<MetaTab />} />
            </Route>
            <Route path="*" element={<p className="text-ink-3">Page not found.</p>} />
          </Route>
        </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
