export type AgentStatus = 'idle' | 'working' | 'waiting' | 'completed' | 'error'

export type AgentTier = 'leadership' | 'data' | 'ai-ml' | 'domain' | 'engineering' | 'research'

export interface Agent {
  id: string
  name: string
  displayName: string
  tier: AgentTier
  status: AgentStatus
  currentTask?: string
  progress?: number
  collaboratingWith?: string[]
  color: string
  icon: string
  location?: 'boss-room' | 'tea-room' | 'game-room'
}

export interface WorkLog {
  id: string
  timestamp: Date
  agentId: string
  agentName: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

export interface OfficeRoom {
  id: string
  name: string
  tier: AgentTier
  agents: Agent[]
  icon: string
  position: { row: number; col: number }
}

export interface SpeechBubble {
  id: string
  agentId: string
  text: string
  timestamp: Date
}

/** 後端推送的分析結果 */
export interface AnalysisResultPayload {
  chart_type: string
  title: string
  data: Array<Record<string, number | string>>
  metadata?: Record<string, number | string>
}

/** Workflow 重試事件 */
export interface WorkflowRetryEvent {
  step_name: string
  attempt: number
  max_retries: number
  delay_seconds: number
}

/** Workflow 降級事件 */
export interface WorkflowDegradationEvent {
  step_name: string
  strategy: 'skip' | 'fallback' | 'abort'
  reason?: string
  fallback_agents?: string[]
}

/** Workflow Checkpoint 事件 */
export interface WorkflowCheckpointEvent {
  step_name: string
  status: 'evaluating' | 'passed' | 'passed_after_rerun' | 'rerunning' | 'failed'
  description?: string
  quality_rules?: Record<string, number>
  rerun?: number
  max_reruns?: number
  adjusted_params?: Record<string, unknown>
  violations?: Array<{ metric: string; value: number; threshold: number }>
}

/** 告警嚴重程度 */
export type AlertSeverity = 'critical' | 'warning' | 'info'

/** 告警處理狀態 */
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'dismissed'

/** 告警資料 */
export interface Alert {
  id: string
  turbine_id: string | null
  source: string
  severity: AlertSeverity
  title: string
  description: string
  status: AlertStatus
  task_id: string | null
  agent_id: string | null
  source_system: string | null
  source_alert_id: string | null
  tags: string[]
  metrics: Record<string, unknown>
  metadata: Record<string, unknown>
  created_at: string
  occurred_at: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  resolved_by: string | null
  work_order_id: string | null
}

/** 工單優先程度 */
export type WorkOrderPriority = 'critical' | 'high' | 'medium' | 'low'

/** 工單處理狀態 */
export type WorkOrderStatus = 'open' | 'in_progress' | 'completed' | 'cancelled'

/** 工單備註 */
export interface WorkOrderNote {
  timestamp: string
  author: string
  text: string
}

/** 工單資料 */
export interface WorkOrder {
  id: string
  alert_id: string | null
  turbine_id: string | null
  title: string
  description: string
  priority: WorkOrderPriority
  status: WorkOrderStatus
  assigned_agents: string[]
  estimated_duration_hours: number | null
  notes: WorkOrderNote[]
  created_at: string
  started_at: string | null
  completed_at: string | null
  metadata: Record<string, unknown>
}

/** 已完成任務的歷史記錄 */
export interface TaskRecord {
  id: string
  description: string
  timestamp: string  // ISO 8601
  durationMs: number
  agentIds: string[]
  agentNames: string[]
  analysisResults: AnalysisResultPayload[]
  extractedMetrics: Array<{ name: string; value: number; agent: string; timestamp: number }>
  workLogSnapshot: Array<{
    id: string
    timestamp: string
    agentId: string
    agentName: string
    message: string
    type: 'info' | 'success' | 'warning' | 'error'
  }>
  status: 'completed' | 'error'
}
