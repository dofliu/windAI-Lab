import { useState } from 'react'
import { Agent } from '../types/agent'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAgentSimulation } from '../hooks/useAgentSimulation'
import OfficeFloor from './OfficeFloor'
import AgentDetail from './AgentDetail'
import WorkLogPanel from './WorkLogPanel'
import CommandBar from './CommandBar'

export default function App() {
  // Try WebSocket first, fall back to simulation
  const ws = useWebSocket()
  const sim = useAgentSimulation()

  const isConnected = ws.connectionStatus === 'connected'
  const hasAgents = ws.agents.length > 0

  // Use WebSocket data if connected and has agents, otherwise use simulation
  const agents = isConnected && hasAgents ? ws.agents : sim.agents
  const rooms = isConnected && hasAgents ? ws.rooms : sim.rooms
  const workLogs = isConnected && hasAgents ? ws.workLogs : sim.workLogs

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const currentSelected = selectedAgent
    ? agents.find((a) => a.id === selectedAgent.id) ?? null
    : null

  const workingCount = agents.filter((a) => a.status === 'working').length

  const connectionLabel = {
    connected: { text: '後端已連線', color: 'text-emerald-400', dot: 'bg-emerald-400' },
    connecting: { text: '連線中...', color: 'text-yellow-400', dot: 'bg-yellow-400' },
    disconnected: { text: '模擬模式（後端離線）', color: 'text-orange-400', dot: 'bg-orange-400' },
    error: { text: '連線錯誤（模擬模式）', color: 'text-red-400', dot: 'bg-red-400' },
  }[ws.connectionStatus]

  return (
    <div className="flex h-screen flex-col bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-700/50 bg-slate-800/80 px-6 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="mr-2">🏢</span>
            WindAI Lab 虛擬研究室
          </h1>
          <span className="rounded-full bg-slate-700/60 px-3 py-0.5 text-xs text-slate-400">
            Phase 1 — {agents.length} 位研究員
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-400">
            {workingCount} 位工作中
          </span>
          <div className="flex items-center gap-1.5">
            <span className={`status-dot h-2 w-2 ${connectionLabel.dot} ${isConnected ? 'animate-pulse-slow' : ''}`} />
            <span className={`text-xs ${connectionLabel.color}`}>{connectionLabel.text}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Office Floor + Command Bar + Work Log */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Office Floor */}
          <div className="flex-1 overflow-y-auto">
            <OfficeFloor
              rooms={rooms}
              selectedAgent={currentSelected}
              onSelectAgent={setSelectedAgent}
            />
          </div>

          {/* Command Bar */}
          <div className="border-t border-slate-700/50 bg-slate-800/60 px-4 py-3">
            <CommandBar
              onExecute={ws.sendCommand}
              disabled={!isConnected}
            />
          </div>

          {/* Work Log Panel */}
          <div className="h-48 shrink-0 border-t border-slate-700/50 bg-slate-850">
            <WorkLogPanel logs={workLogs} />
          </div>
        </div>

        {/* Agent Detail Sidebar */}
        <aside className="w-72 shrink-0 border-l border-slate-700/50 bg-slate-800/50">
          <AgentDetail
            agent={currentSelected}
            allAgents={agents}
            workLogs={workLogs}
          />
        </aside>
      </div>
    </div>
  )
}
