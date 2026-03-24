import { useState } from 'react'
import { Agent } from '../types/agent'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAgentSimulation } from '../hooks/useAgentSimulation'
import OfficeWorld from './OfficeWorld'
import Sidebar from './Sidebar'
import CommandBar from './CommandBar'

export default function App() {
  // Try WebSocket first, fall back to simulation
  const ws = useWebSocket()
  const sim = useAgentSimulation()

  const isConnected = ws.connectionStatus === 'connected'
  // Only use WebSocket data when the backend actively sends live updates
  // (not just the static initial_state on connect)
  const useLiveBackend = isConnected && ws.hasLiveUpdates

  const agents = useLiveBackend ? ws.agents : sim.agents
  const rooms = useLiveBackend ? ws.rooms : sim.rooms
  const workLogs = useLiveBackend ? ws.workLogs : sim.workLogs
  const speechBubbles = useLiveBackend ? ws.speechBubbles : sim.speechBubbles

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const currentSelected = selectedAgent
    ? agents.find((a) => a.id === selectedAgent.id) ?? null
    : null

  const workingCount = agents.filter((a) => a.status === 'working').length

  // Simulation-only commands always go to sim; others route based on backend status
  const SIM_COMMANDS = new Set(['bosscall', 'teatime'])

  const handleCommand = (command: string, parameters: Record<string, string>) => {
    // Always run simulation commands locally
    sim.sendCommand(command, parameters)
    // Also forward non-sim commands to backend if live
    if (useLiveBackend && !SIM_COMMANDS.has(command)) {
      ws.sendCommand(command, parameters)
    }
  }

  const connectionLabel = useLiveBackend
    ? { text: '後端已連線', color: 'text-emerald-400', dot: 'bg-emerald-400' }
    : {
        connected: { text: '模擬模式（後端無即時資料）', color: 'text-cyan-400', dot: 'bg-cyan-400' },
        connecting: { text: '連線中...', color: 'text-yellow-400', dot: 'bg-yellow-400' },
        disconnected: { text: '模擬模式', color: 'text-orange-400', dot: 'bg-orange-400' },
        error: { text: '模擬模式', color: 'text-orange-400', dot: 'bg-orange-400' },
      }[ws.connectionStatus]

  return (
    <div className="flex h-screen flex-col bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-700/50 bg-slate-800/80 px-6 py-2 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600/20">
              <span className="text-sm">🏢</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight">WindAI Lab</h1>
              <p className="text-[9px] text-slate-500">虛擬研究辦公室</p>
            </div>
          </div>
          <span className="rounded-full bg-slate-700/60 px-2 py-0.5 text-[9px] text-slate-400">
            {agents.length} 位研究員
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400/80" />
              {workingCount} 工作中
            </span>
            <span className="text-slate-600">|</span>
            <span>{agents.length - workingCount} 待命</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${connectionLabel.dot} ${useLiveBackend ? 'animate-pulse-slow' : ''}`} />
            <span className={`text-[9px] ${connectionLabel.color}`}>{connectionLabel.text}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Office World + Command Bar */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Office World (pixel art) — takes all remaining space */}
          <div className="flex-1 overflow-x-hidden overflow-y-auto">
            <OfficeWorld
              rooms={rooms}
              selectedAgent={currentSelected}
              onSelectAgent={setSelectedAgent}
              speechBubbles={speechBubbles}
            />
          </div>

          {/* Command Bar (compact) */}
          <div className="border-t border-slate-700/50 bg-slate-800/60 px-4 py-2">
            <CommandBar
              onExecute={handleCommand}
            />
          </div>
        </div>

        {/* Sidebar: Agent Detail + Work Logs (tabbed) */}
        <aside className="w-72 shrink-0 border-l border-slate-700/50 bg-slate-800/50">
          <Sidebar
            agent={currentSelected}
            allAgents={agents}
            workLogs={workLogs}
          />
        </aside>
      </div>
    </div>
  )
}
