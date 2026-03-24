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
