import { useOutletContext } from 'react-router-dom'

import type { PlayerResponse } from '../../api/types'

export interface PlayerCtx {
  tag: string
  player: PlayerResponse
}

export const usePlayerCtx = () => useOutletContext<PlayerCtx>()
