// ─── Domain enums ─────────────────────────────────────────────────────────────

export type NodeType = 'start' | 'transform' | 'http' | 'delay' | 'branch' | 'end'

export type RunStatus = 'pending' | 'running' | 'completed' | 'failed'

export type EventStatus = 'running' | 'completed' | 'failed' | 'skipped'

// ─── Graph model ──────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string
  type: NodeType
  position: { x: number; y: number }
  data: {
    label: string
    config: Record<string, unknown>
  }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  /** Only present on edges leaving a `branch` node */
  data?: { branch?: 'true' | 'false' }
}

export interface Graph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ─── Workflow ─────────────────────────────────────────────────────────────────

export interface WorkflowIn {
  name: string
  description?: string
  graph: Graph
}

export interface WorkflowOut {
  id: string
  name: string
  description?: string
  graph: Graph
  created_at: string
  updated_at: string
}

// ─── Run ──────────────────────────────────────────────────────────────────────

export interface RunOut {
  id: string
  workflow_id: string
  status: RunStatus
  trigger_payload: Record<string, unknown>
  final_payload?: Record<string, unknown> | null
  error?: string | null
  started_at?: string | null
  finished_at?: string | null
}

// ─── Execution event (time-travel log) ───────────────────────────────────────

export interface ExecutionEventOut {
  id: string
  run_id: string
  node_id: string
  sequence: number
  status: EventStatus
  input_snapshot: Record<string, unknown>
  output?: Record<string, unknown> | null
  error?: string | null
  started_at: string
  finished_at?: string | null
  duration_ms?: number | null
}

// ─── Validation ───────────────────────────────────────────────────────────────

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

// ─── Convenience: node config shapes ─────────────────────────────────────────

export interface TransformConfig {
  mappings: Record<string, string>
}

export interface HttpConfig {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  url: string
  headers?: Record<string, string>
  body?: Record<string, unknown>
}

export interface DelayConfig {
  seconds: number
}

export interface BranchConfig {
  condition: string
}
