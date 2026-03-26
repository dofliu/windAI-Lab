import { useState, useMemo, useCallback, useRef } from 'react'
import { Agent, SpeechBubble } from '../types/agent'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAgentSimulation } from '../hooks/useAgentSimulation'
import { useTheme } from '../themes'
import { initialRooms } from '../utils/mockData'
import CompactOffice from './CompactOffice'
import DashboardView from './DashboardView'
import MissionView from './MissionView'
import OfficeWorld from './OfficeWorld'
import CommandBar from './CommandBar'

export default function App() {
  const ws = useWebSocket()
  const sim = useAgentSimulation()
  const { theme } = useTheme()

  const isConnected = ws.connectionStatus === 'connected'
  const hasBackend = isConnected && ws.hasLiveUpdates

  /* ════════════════════════════════════════════════════════════════
     Merged state: simulation is ALWAYS the living base.
     When the backend actively manages specific agents (non-idle),
     those agents' status overlays on top of the simulation.
     ════════════════════════════════════════════════════════════════ */

  /* ── Hire / Fire state (must be before agents useMemo) ── */
  const [extraAgents, setExtraAgents] = useState<Agent[]>([])

  const backendActiveIds = useMemo(() => {
    if (!hasBackend) return new Set<string>()
    return new Set(
      ws.agents.filter((a) => a.status !== 'idle' && a.status !== 'completed').map((a) => a.id),
    )
  }, [hasBackend, ws.agents])

  const agents = useMemo(() => {
    let base: Agent[]
    if (!hasBackend) {
      base = sim.agents
    } else {
      const wsMap = new Map(ws.agents.map((a) => [a.id, a]))
      base = sim.agents.map((a) => {
        if (backendActiveIds.has(a.id)) return wsMap.get(a.id) ?? a
        return a
      })
    }
    // 合併動態聘用的代理
    const baseIds = new Set(base.map(a => a.id))
    const extra = extraAgents.filter(a => !baseIds.has(a.id))
    return [...base, ...extra]
  }, [hasBackend, sim.agents, ws.agents, backendActiveIds, extraAgents])

  // Rooms (for OfficeWorld pixel mode)
  const rooms = useMemo(
    () =>
      initialRooms.map((room) => ({
        ...room,
        agents: agents.filter((a) => a.tier === room.tier),
      })),
    [agents],
  )

  // Speech bubbles
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

  const workLogs = useMemo(() => {
    if (!hasBackend) return sim.workLogs
    return [...sim.workLogs, ...ws.workLogs]
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
      .slice(-100)
  }, [hasBackend, sim.workLogs, ws.workLogs])

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(260)
  const isDragging = useRef(false)

  // Threshold: >=550px shows pixel animation OfficeWorld
  const PIXEL_MODE_THRESHOLD = 550

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    const startX = e.clientX
    const startW = sidebarWidth

    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current) return
      const newW = Math.max(48, Math.min(900, startW + (ev.clientX - startX)))
      setSidebarWidth(newW)
      if (newW <= 48) setSidebarCollapsed(true)
      else setSidebarCollapsed(false)
    }
    const onUp = () => {
      isDragging.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [sidebarWidth])

  const currentSelected = selectedAgent
    ? agents.find((a) => a.id === selectedAgent.id) ?? null
    : null

  const workingCount = agents.filter((a) => a.status === 'working').length

  // ── 戰情中心模式：有代理在工作中且來自後端（非模擬閒聊）──
  const isMissionMode = useMemo(() => {
    if (!hasBackend) return false
    return agents.some(
      (a) => backendActiveIds.has(a.id) && (a.status === 'working' || a.status === 'waiting'),
    )
  }, [hasBackend, agents, backendActiveIds])

  /* ── Hire / Fire handlers (simulation mode) ── */
  const handleHire = useCallback((agent: { id: string; name: string; display_name: string; tier: string; color: string; icon: string }) => {
    const newAgent: Agent = {
      id: agent.id,
      name: agent.name,
      displayName: agent.display_name,
      tier: agent.tier as Agent['tier'],
      status: 'idle',
      color: agent.color,
      icon: agent.icon,
    }
    setExtraAgents(prev => [...prev, newAgent])
  }, [])

  const handleFire = useCallback((agentId: string) => {
    setExtraAgents(prev => prev.filter(a => a.id !== agentId))
  }, [])

  /* ── Command routing ── */
  const SIM_COMMANDS = new Set(['bosscall', 'teatime'])

  const handleCommand = (command: string, parameters: Record<string, string>) => {
    sim.sendCommand(command, parameters)
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
    <div
      className="flex h-screen flex-col"
      style={{ backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
    >
      {/* ── Header ── */}
      <header
        className="flex items-center justify-between border-b px-4 py-2 backdrop-blur-sm"
        style={{ borderColor: theme.global.border, backgroundColor: theme.global.headerBg + 'cc' }}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div
              className="flex h-7 w-7 items-center justify-center rounded-lg"
              style={{ backgroundColor: theme.global.accent + '33' }}
            >
              <span className="text-sm">{isMissionMode ? '\u{1F3DB}' : '\u{1F3E2}'}</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight">WindAI Lab</h1>
              <p className="text-[9px]" style={{ color: theme.global.textMuted }}>
                {isMissionMode ? '戰情中心' : '虛擬研究辦公室'}
              </p>
            </div>
          </div>
          <span
            className="rounded-full px-2 py-0.5 text-[9px]"
            style={{ backgroundColor: theme.global.border, color: theme.global.textSecondary }}
          >
            {agents.length} 位研究員
          </span>
          {isMissionMode && (
            <span
              className="rounded-full px-2 py-0.5 text-[9px] animate-pulse-slow"
              style={{ backgroundColor: theme.statuses.working.bg, color: theme.statuses.working.dot }}
            >
              任務進行中
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-[10px]" style={{ color: theme.global.textSecondary }}>
            <span className="flex items-center gap-1">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: theme.statuses.working.dot + 'cc' }}
              />
              {workingCount} 工作中
            </span>
            <span style={{ color: theme.global.textMuted }}>|</span>
            <span>{agents.length - workingCount} 待命</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${connectionLabel.dot} ${hasBackend ? 'animate-pulse-slow' : ''}`} />
            <span className={`text-[9px] ${connectionLabel.color}`}>{connectionLabel.text}</span>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <div className="flex flex-1 overflow-hidden">
        {isMissionMode ? (
          /* ══ 戰情中心模式 ══ */
          <MissionView
            agents={agents}
            workLogs={workLogs}
            onAgentClick={setSelectedAgent}
          />
        ) : (
          /* ══ 一般辦公室模式 ══ */
          <>
            {/* Left: Resizable Office Panel */}
            <aside
              className="shrink-0 border-r overflow-hidden"
              style={{
                width: sidebarCollapsed ? 48 : sidebarWidth,
                borderColor: theme.global.border,
                backgroundColor: theme.global.panelBg + '80',
              }}
            >
              {/* Toggle button */}
              <div
                className="flex items-center justify-between border-b px-2 py-1"
                style={{ borderColor: theme.global.border + '66' }}
              >
                {!sidebarCollapsed && sidebarWidth >= PIXEL_MODE_THRESHOLD && (
                  <span className="text-[8px]" style={{ color: theme.global.textMuted }}>🎮 像素模式</span>
                )}
                {!sidebarCollapsed && sidebarWidth < PIXEL_MODE_THRESHOLD && (
                  <span className="text-[8px]" style={{ color: theme.global.textMuted }}>← 拖拉邊框調寬度</span>
                )}
                <button
                  onClick={() => {
                    if (sidebarCollapsed) {
                      setSidebarCollapsed(false)
                      setSidebarWidth(260)
                    } else {
                      setSidebarCollapsed(true)
                    }
                  }}
                  className="ml-auto rounded p-1 transition-colors hover:opacity-80"
                  style={{ color: theme.global.textMuted }}
                  title={sidebarCollapsed ? '展開研究室面板' : '收合研究室面板'}
                >
                  <svg
                    className={`h-3.5 w-3.5 transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
              </div>

              {/* Office content — switches between compact and pixel mode */}
              <div className="h-[calc(100%-32px)] overflow-hidden">
                {sidebarWidth >= PIXEL_MODE_THRESHOLD && !sidebarCollapsed ? (
                  <div className="h-full overflow-y-auto overflow-x-hidden">
                    <OfficeWorld
                      rooms={rooms}
                      selectedAgent={currentSelected}
                      onSelectAgent={setSelectedAgent}
                      speechBubbles={speechBubbles}
                    />
                  </div>
                ) : (
                  <CompactOffice
                    agents={agents}
                    selectedAgent={currentSelected}
                    onSelectAgent={setSelectedAgent}
                    collapsed={sidebarCollapsed}
                  />
                )}
              </div>
            </aside>

            {/* Drag handle */}
            {!sidebarCollapsed && (
              <div
                onMouseDown={handleMouseDown}
                className="w-1.5 shrink-0 cursor-col-resize transition-colors hover:opacity-70"
                style={{ backgroundColor: theme.global.border + '4d' }}
                title="拖拉調整寬度"
              />
            )}

            {/* Right: Dashboard + CommandBar */}
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="flex-1 overflow-hidden">
                <DashboardView
                  workLogs={workLogs}
                  selectedAgent={currentSelected}
                  allAgents={agents}
                  fileEvents={ws.fileEvents ?? []}
                  onHireAgent={handleHire}
                  onFireAgent={handleFire}
                />
              </div>

              {/* Command Bar */}
              <div
                className="border-t px-4 py-2"
                style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg + '99' }}
              >
                <CommandBar onExecute={handleCommand} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Command Bar (always visible, even in mission mode) */}
      {isMissionMode && (
        <div
          className="border-t px-4 py-2"
          style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg + '99' }}
        >
          <CommandBar onExecute={handleCommand} />
        </div>
      )}
    </div>
  )
}
