// Response shapes of the FastAPI backend (only the fields the UI reads).

export type Rarity = 'common' | 'rare' | 'epic' | 'legendary' | 'champion'
export type Form = 'evo' | 'hero' | null

export interface SlimCard {
  id: number
  name: string
  rarity: Rarity | null
  elixir: number | null
  form: Form
  icon: string | null
  level?: number
}

export interface Rate {
  games: number
  wins: number
  losses: number
  draws: number
  win_rate: number | null
  ci_low: number | null
  ci_high: number | null
}

export interface PolResult {
  leagueNumber: number
  trophies: number
  rank: number | null
}

export interface PlayerSummary {
  tag: string
  name: string
  trophies: number
  best_trophies: number
  legacy_best_trophies: number | null
  arena: string | null
  king_tower_level: number | null
  collection_level: number | null
  wins: number
  losses: number
  win_rate: number | null
  battle_count: number
  three_crown_wins: number
  three_crown_rate: number | null
  win_streak: number | null
  challenge_max_wins: number | null
  challenge_cards_won: number | null
  tournament_battles: number | null
  donations: number | null
  donations_received: number | null
  total_donations: number | null
  war_day_wins: number | null
  star_points: number | null
  days_played: number | null
  clan: { tag: string; name: string; badgeId: number } | null
  role: string | null
  ranked: { current: PolResult | null; last: PolResult | null; best: PolResult | null }
  current_deck: SlimCard[]
  current_deck_avg_elixir: number | null
  current_deck_avg_level: number | null
  tower_troop: SlimCard | null
  favourite_card: SlimCard | null
  other_modes: { key: string; arena: string | null; trophies: number; best_trophies: number }[]
}

export interface PlayerResponse {
  summary: PlayerSummary
  tracked: boolean
  last_refreshed_at: string | null
  battles_stored: number
  snapshots_stored: number
}

export interface TrackedPlayer {
  tag: string
  name: string
  trophies: number | null
  last_refreshed_at: string | null
}

export interface Snapshot {
  time: string
  trophies: number
  best_trophies: number
  king_tower_level: number | null
  collection_level: number | null
  wins: number
  losses: number
  battle_count: number
  three_crown_wins: number
  pol_league: number | null
  pol_trophies: number | null
  mastery_levels: number
  cards_maxed: number
  avg_card_level: number | null
}

export interface Delta {
  since: string
  trophies: number
  collection_level: number | null
  king_tower_level: number | null
  wins: number
  battles: number
  mastery_levels: number
  cards_maxed: number
}

export interface ProgressResponse {
  snapshots: Snapshot[]
  trophy_path: { time: string; mode: string; trophies: number; change: number; result: string }[]
  deltas: { day?: Delta | null; week?: Delta | null; month?: Delta | null }
}

export interface Insight {
  level: 'good' | 'warn' | 'info'
  text: string
}

export interface CardRate extends Rate {
  id: number
  name: string
  icon: string | null
  delta?: number
  level?: number
}

export interface AnalyticsResponse {
  mode: string
  days: number | null
  timezone: string
  summary: Rate & {
    three_crown_wins: number
    three_crowned: number
    avg_elixir_leaked: number | null
    avg_level_gap: number | null
    net_trophies: number
    avg_trophies_win: number | null
    avg_trophies_loss: number | null
    first_battle: string | null
    last_battle: string | null
  }
  by_mode: (Rate & { mode: string })[]
  timeline: {
    daily: (Rate & { date: string; net_trophies: number })[]
    hourly: (Rate & { hour: number })[]
    weekday: (Rate & { weekday: number })[]
  }
  tilt: {
    current: { kind: string | null; length: number }
    longest_win_streak: number
    longest_loss_streak: number
    after_win: Rate
    after_loss: Rate
    after_2_losses: Rate
    after_3_wins: Rate
    sessions: {
      count: number
      avg_length: number
      by_game_index: (Rate & { index: string })[]
      recent: (Rate & { start: string; end: string; net_trophies: number })[]
    }
  }
  levels: {
    buckets: (Rate & { bucket: string })[]
    losses_underleveled: number
    losses_total: number
    share_losses_underleveled: number | null
    even_level: Rate
  }
  close_games: {
    margins: { margin: number; games: number }[]
    one_crown: Rate
    blowouts: Rate
    one_crown_losses: number
    near_miss_tower_hp: number | null
    avg_king_hp_left_in_wins: number | null
  }
  elixir: { buckets: (Rate & { bucket: string })[]; avg_in_wins: number | null; avg_in_losses: number | null }
  evolutions: {
    by_my_evos: (Rate & { count: number })[]
    with_hero: Rate
    without_hero: Rate
    special_advantage: (Rate & { bucket: string })[]
  }
  matchups: {
    min_games: number
    nemesis: CardRate[]
    prey: CardRate[]
    most_faced: CardRate[]
    archetypes: (Rate & { archetype: string })[]
  }
  decks: (Rate & { archetype: string; cards: SlimCard[]; avg_elixir: number | null; last_played: string })[]
  cards: CardRate[]
  tower_troops: (Rate & { tower_troop: string })[]
  insights: Insight[]
}

export interface Battle {
  id: string
  battle_time: string
  type: string
  game_mode: string
  mode_group: string
  result: 'win' | 'loss' | 'draw' | 'unknown'
  crowns: number | null
  opp_crowns: number | null
  trophy_change: number | null
  starting_trophies: number | null
  elixir_leaked: number | null
  opp_name: string | null
  opp_tag: string | null
  opp_clan: string | null
  deck: SlimCard[]
  opp_deck: SlimCard[]
  avg_level: number | null
  opp_avg_level: number | null
  archetype: string
  opp_archetype: string
  king_hp: number | null
  opp_king_hp: number | null
  princess_hp: number[]
  opp_princess_hp: number[]
}

export interface CardPlan {
  id: number
  name: string
  rarity: Rarity
  elixir: number | null
  icon: string | null
  level: number
  count: number
  maxed: boolean
  next_cards: number | null
  next_gold: number | null
  can_upgrade: boolean
  copies_missing_next: number
  levels_affordable: number
  gold_for_affordable: number
  to_max_cards: number
  to_max_gold: number
  to_target_cards: number
  to_target_gold: number
  usage: number
  vs_opponents?: number | null
}

export interface UpgradesResponse {
  target_level: number
  opponent_avg_level: number | null
  games_analyzed: number
  deck: CardPlan[]
  deck_summary: {
    avg_level: number | null
    gold_to_target: number
    copies_missing_to_target: number
    cards_at_target: number
    gold_to_max: number
    gold_for_affordable: number
  }
  upgradable_now: CardPlan[]
  closest_blocked: CardPlan[]
  collection_summary: {
    cards: number
    maxed: number
    upgradable_now: number
    gold_to_max_all: number
    gold_for_all_affordable: number
    by_level: Record<string, number>
  }
  cards: CardPlan[]
  notes: string[]
}

export interface Badge {
  badge: string
  level: number | null
  max_level: number | null
  progress: number
  target: number | null
  icon: string | null
  maxed: boolean
  completion: number
  card?: string
  card_icon?: string | null
  card_level?: number
  title?: string
}

export interface MasteryResponse {
  mastery: Badge[]
  closest_mastery: Badge[]
  mastery_total_levels: number
  mastery_maxed: number
  mastery_started: number
  cards_without_mastery: number
  badges: Badge[]
  achievements: { name: string; info: string; stars: number; value: number; target: number; completion: number }[]
}

export interface Chest {
  index: number
  name: string
}

export interface MetaCard {
  id: number
  name: string
  icon: string | null
  elixir: number | null
  rarity: Rarity | null
  usage: number
  special_form_rate: number
  games: number
  win_rate: number | null
  ci_low: number
  ci_high: number
}

export interface MetaResponse {
  mode: string
  days: number
  decks_observed: number
  matches: number
  cards: MetaCard[]
  archetypes: { archetype: string; usage: number; games: number; win_rate: number | null }[]
  top_decks: { archetype: string; cards: SlimCard[]; games: number; win_rate: number | null; ci_low: number; ci_high: number }[]
}

export interface MetaStatus {
  running: boolean
  last_crawl: {
    id: number
    started_at: string
    finished_at: string | null
    status: 'running' | 'done' | 'failed'
    source: string
    players_total: number
    players_done: number
    battles_added: number
    error: string | null
  } | null
}

export interface MetaCompareResponse {
  mode: string
  days: number
  decks_observed: number
  my_cards: { id: number; name: string; icon: string | null; meta_usage: number; meta_win_rate: number | null; meta_games: number }[]
  exact_matches: { games: number; win_rate: number | null }
  similar_decks: { shared: number; archetype: string; cards: SlimCard[]; games: number; win_rate: number; missing: SlimCard[] }[]
  swap_suggestions: (MetaCard & { in_similar_decks: number; similar_win_rate: number })[]
  off_meta_cards: { id: number; name: string; meta_usage: number }[]
}

export interface ClanMember {
  tag: string
  name: string
  role: string
  trophies: number
  arena: string | null
  clan_rank: number
  donations: number
  donations_received: number
  last_seen: string | null
  days_inactive: number | null
  war_fame: number
  war_decks_used: number
  war_decks_today: number
  war_boat_attacks: number
}

export interface ClanResponse {
  tag: string
  name: string
  description: string | null
  type: string
  clan_score: number
  war_trophies: number
  required_trophies: number
  donations_per_week: number
  location: string | null
  member_count: number
  members: ClanMember[]
  river_race: {
    period_type: string | null
    is_war_day: boolean
    decks_per_day: number
    standings: { tag: string; name: string; fame: number; period_points: number; finished: boolean; is_us: boolean }[]
    members_missing_decks_today: number
  } | null
}

export interface Health {
  status: string
  version: string
  api_key_configured: boolean
  default_player_tag: string | null
}
