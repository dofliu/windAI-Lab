import { useState, useMemo } from 'react'
import { Agent, SpeechBubble } from '../types/agent'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAgentSimulation } from '../hooks/useAgentSimulation'
import { initialRooms } from '../utils/mockData'
import OfficeWorld from './OfficeWorld'
import Sidebar from './Sidebar'
import CommandBar from './CommandBar'

export default function App() {
  const ws = useWebSocket()
  const sim = useAgentSimulation()

  const isConnected = ws.connectionStatus === 'connected'
  const hasBackend = isConnected && ws.hasLiveUpdates

  /* ════════════════════════════════════════════════════════════════
     Merged state: simulation is ALWAYS the living base.
     When the backend actively manages specific agents (non-idle),
     those agents' status overlays on top of the simulation.
     ════════════════════════════════════════════════════════════════ */

  // IDs of agents the backend is actively managing (working/waiting/error)
  const backendActiveIds = useMemo(() => {
    if (!hasBackend) return new Set<string>()
    return new Set(
      ws.agents.filter((a) => a.status !== 'idle' && a.status !== 'completed').map((a) => a.id),
    )
  }, [hasBackend, ws.agents])

  // Agents: sim base + backend overlay for active agents
  const agents = useMemo(() => {
    if (!hasBackend) return sim.agents
    const wsMap = new Map(ws.agents.map((a) => [a.id, a]))
    return sim.agents.map((a) => {
      if (backendActiveIds.has(a.id)) return wsMap.get(a.id) ?? a
      return a
    })
  }, [hasBackend, sim.agents, ws.agents, backendActiveIds])

  // Rooms: derived from merged agents
  const rooms = useMemo(
    () =>
      initialRooms.map((room) => ({
        ...room,
        agents: agents.filter((a) => a.tier === room.tier),
      })),
    [agents],
  )

  // Speech bubbles: merge both (latest per agent wins)
  const speechBubbles = useMemo(() => {
    if (!hasBackend) return sim.speechBubbles
    const merged = new Map<string, SpeechBubble>()
    sim.speechBubbles.forEach((b) => merged.set(b.agentId, b))
    ws.speechBubbles.forEach((b) => {
      const existing = merged.get(b.agentId)
      if (!existing || b.timestamp > existing.timestamp) {
        merged.set(b.agentId, b)
      }
    })
    return Array.from(merged.values())
  }, [hasBackend, sim.speechBubbles, ws.speechBubbles])

  // Work logs: merge both sources
  const workLogs = useMemo(() => {
    if (!hasBackend) return sim.workLogs
    return [...sim.workLogs, ...ws.workLogs]
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
      .slice(-100)
  }, [hasBackend, sim.workLogs, ws.workLogs])

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const currentSelected = selectedAgent
    ? agents.find((a) => a.id === selectedAgent.id) ?? null
    : null

  const workingCount = agents.filter((a) => a.status === 'working').length

  /* ── Command routing ── */
  const SIM_COMMANDS = new Set(['bosscall', 'teatime'])

  const handleCommand = (command: string, parameters: Record<string, string>) => {
    // Simulation always handles its own commands (bosscall, teatime)
    sim.sendCommand(command, parameters)
    // Forward real workflow commands to backend when connected
    if (isConnected && !SIM_COMMANDS.has(command)) {
      ws.sendCommand(command, parameters)
    }
  }

  /* ── Connection label ── */
  const connectionLabel = hasBackend
    ? { text: '混合模式（後端 + 模擬）', color: 'text-emerald-400', dot: 'bg-emerald-400' }
    : {
        connected: { text: '模擬模式（後端已連線）', color: 'text-cyan-400', dot: 'bg-cyan-400' },
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
            <span className={`h-1.5 w-1.5 rounded-full ${connectionLabel.dot} ${hasBackend ? 'animate-pulse-slow' : ''}`} />
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
