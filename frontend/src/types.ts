export interface WorldSummary {
  world_id: string
  title: string
  archetype_id: string
  created_by: string
  seed: number
  target_difficulty: number
  viable: boolean
}
export interface WorldFull extends WorldSummary {
  briefing: string
  specification: string
  starter_source: string
  function_name: string
  function_signature: string
  mandatory_properties: string[]
  optional_objectives: string[]
  sample_input_description: string
  cohort?: { code: string; name: string; display_name: string } | null
}
export interface TestResult { test: string; passed: boolean; hidden?: boolean }
export interface SubmitResult {
  verdict: 'accepted' | 'rejected'
  reason?: string | null
  detail?: string | null
  tests: TestResult[]
}
export interface Archetype { id: string; title: string; domain: string }

export interface RatingChange { before: number; after: number; counted: boolean }
export interface SubmitResultWithRating extends SubmitResult { rating?: RatingChange }

// --- Probe lab -------------------------------------------------------------
export interface ProbeInfo {
  kind: 'job_queue' | 'pool'
  help: string
  template: Record<string, unknown>
  limits: Record<string, number>
  day_length?: number
  noun?: string
  machine?: string
  pool_size?: number
  unit?: string
  checkout_func?: string
  release_func?: string
}
export interface JobRow {
  id: number; minutes: number; submitted_at: number
  started_at: number | null; finished_at: number | null
  status: 'finished' | 'rejected' | 'abandoned' | 'running' | 'never_started'
  wait: number | null; abandon_at: number | null; entry: number | null; owner: string | null
}
export interface JobEvent { t: number; kind: string; id: number }
export interface JobTrace {
  kind: 'job_queue'; day_length: number; jobs: JobRow[]; events: JobEvent[]
  events_truncated: boolean
  stats: {
    busy_minutes: number; open_minutes: number; idle_while_waiting: number
    too_late_attempts: number; invalid_picks: number; days_simulated: number
    event_count: number; max_queue: number
  }
}
export interface PoolOp {
  k: number; op: 'checkout' | 'release'; holder: number; returned: number
  outcome: 'got_slot' | 'denied' | 'invalid_slot' | 'accepted' | 'refused'
  in_use: number; ledger: number; entry: number | null
}
export interface PoolTrace {
  kind: 'pool'; pool_size: number; ops: PoolOp[]; ops_truncated: boolean
  slots: { slot: number; in_use: boolean; holder: number }[]
  stats: { pool_size: number; in_use: number; ledger: number; op_count: number }
}
export interface ProbeResult {
  ok: boolean; error: string | null; detail: string | null
  trace: JobTrace | PoolTrace | Record<string, never>
  ran: 'original' | 'yours'
}

// --- Witnesses -------------------------------------------------------------
export interface Witness {
  key: string; name: string; role: string; vantage: string
  questions: { topic: string; question: string }[]
}
export interface Evidence { columns: string[]; rows: (string | number)[][]; total?: number }
export interface WitnessAnswer {
  witness: string; topic: string; text: string
  evidence?: Evidence | null
  followups?: string[]
  error?: string; detail?: string
  replay?: { text: string; evidence?: Evidence | null; error?: string; detail?: string }
}

// --- Profiles --------------------------------------------------------------
export interface Profile {
  user_id: string; rating: number; level: string; recommended_difficulty: number
  worlds_solved: number; worlds_attempted: number; submissions: number
  experiments_run: number; witness_questions: number
  history: { world_id: string; difficulty: number; verdict: string; passed: number; total: number
             rating_before: number; rating_after: number; at: string }[]
}

// --- Cohorts ---------------------------------------------------------------
export interface Cohort {
  code: string; name: string; archetype_id: string; archetype_title: string
  target_difficulty: number; status: 'open' | 'closed'; member_count: number
  host_id: string; created_at: string
  membership?: { user_id: string; display_name: string; world_id: string; joined_at: string } | null
}
export interface CohortMember {
  user_id: string; display_name: string; world_id: string; joined_at: string
  world_exists: boolean; identifiers: string[]; submissions: number; solved: boolean
  solved_at: string | null; best: { passed: number; total: number } | null
  experiments: number; witness_questions: number
}
export interface Originality {
  submissions_compared: number; unchanged_from_starter: string[]; accepted: number
  distinct_approaches: number; approaches: string[][]
  pairs: { a: string; b: string; similarity: number; both_accepted: boolean }[]
  near_identical: { a: string; b: string; similarity: number; both_accepted: boolean }[]
  method: string
}
export interface CohortHostView extends Cohort {
  setting: string | null; defect_variant: string; defect_class: string
  members: CohortMember[]; originality: Originality; solved_count: number
}
