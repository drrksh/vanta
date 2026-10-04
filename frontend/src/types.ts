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
}
export interface TestResult { test: string; passed: boolean }
export interface SubmitResult {
  verdict: 'accepted' | 'rejected'
  reason?: string | null
  detail?: string | null
  tests: TestResult[]
}
export interface Archetype { id: string; title: string; domain: string }
