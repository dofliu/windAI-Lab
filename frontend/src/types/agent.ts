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
