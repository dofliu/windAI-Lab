import { Agent, OfficeRoom } from '../types/agent'
import { tierColors } from '../utils/mockData'
import AgentAvatar from './AgentAvatar'

interface OfficeFloorMapProps {
  rooms: OfficeRoom[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
}

/** Room decoration config */
const roomDeco: Record<string, string[]> = {
  'room-leadership': ['🪴', '☕'],
  'room-data': ['🖥️', '📊'],
  'room-ai-ml': ['🧪', '⚡'],
  'room-domain': ['🌬️', '📐'],
  'room-engineering': ['💻', '🔧'],
  'room-research': ['📖', '✏️'],
}

/** 辦公室房間元件 */
function RoomSection({
  room,
  selectedAgent,
  onSelectAgent,
  meetingAgentIds,
}: {
  room: OfficeRoom
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
  meetingAgentIds: Set<string>
}) {
  const colors = tierColors[room.tier] ?? tierColors['leadership']
  const deco = roomDeco[room.id] ?? []
  // 留在房間裡的代理（不在會議室中的）
  const stayingAgents = room.agents.filter((a) => !meetingAgentIds.has(a.id))
  const inMeetingCount = room.agents.length - stayingAgents.length

  return (
    <div className={`office-room ${colors.bg} relative overflow-hidden border ${colors.border}`}>
      {/* Inner wall effect */}
      <div className="absolute inset-0 rounded-xl border-2 border-slate-600/15 pointer-events-none" />

      {/* Room header */}
      <div className="room-header flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">{room.icon}</span>
          <h3 className={`text-sm font-semibold ${colors.accent}`}>{room.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          {inMeetingCount > 0 && (
            <span className="text-[10px] text-indigo-400/70">
              {inMeetingCount} 在會議室
            </span>
          )}
          <span className="text-[10px] text-slate-500">{room.agents.length} 人</span>
        </div>
      </div>

      {/* Door indicator */}
      <div className="absolute left-1/2 top-0 -translate-x-1/2">
        <div className="h-1 w-8 rounded-b bg-slate-500/30" />
      </div>

      {/* Desks area */}
      <div className="desks-area flex flex-wrap justify-center gap-3 px-3 pb-3 pt-1">
        {stayingAgents.map((agent) => (
          <AgentAvatar
            key={agent.id}
            agent={agent}
            isSelected={selectedAgent?.id === agent.id}
            onSelect={onSelectAgent}
            size={room.agents.length > 8 ? 'sm' : 'md'}
          />
        ))}
        {/* 空桌位 placeholder（代理去了會議室） */}
        {inMeetingCount > 0 && Array.from({ length: inMeetingCount }).map((_, i) => (
          <div key={`empty-${i}`} className="desk-slot flex flex-col items-center opacity-30">
            <div className="desk-surface mb-1 rounded-lg bg-slate-700/20 px-1.5 pb-1.5 pt-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-dashed border-slate-600/40">
                <span className="text-[10px] text-slate-600">會議中</span>
              </div>
              <div className="mt-1 h-1.5 w-8 rounded-sm mx-auto bg-slate-600/15" />
            </div>
          </div>
        ))}
      </div>

      {/* Room decorations */}
      {deco.length > 0 && (
        <div className="absolute bottom-2 right-3 flex gap-1.5 opacity-25">
          {deco.map((d, i) => (
            <span key={i} className="text-xs">{d}</span>
          ))}
        </div>
      )}

      {/* Floor texture */}
      <div
        className="absolute inset-0 rounded-xl pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '16px 16px',
        }}
      />
    </div>
  )
}

/** 會議室元件 — 顯示所有有任務的代理 */
function MeetingRoom({
  agents,
  selectedAgent,
  onSelectAgent,
}: {
  agents: Agent[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
}) {
  if (agents.length === 0) {
    return (
      <div className="meeting-room-empty relative overflow-hidden rounded-xl border border-slate-700/30 bg-slate-800/20 px-4 py-3">
        <div className="flex items-center gap-2 text-slate-600">
          <span className="text-base">🏛️</span>
          <span className="text-xs font-medium">會議室</span>
          <span className="text-[10px]">— 目前沒有進行中的任務</span>
        </div>
      </div>
    )
  }

  return (
    <div className="meeting-room relative overflow-hidden rounded-xl border border-indigo-600/30 bg-indigo-950/20">
      {/* Meeting room glow */}
      <div className="absolute inset-0 rounded-xl pointer-events-none opacity-30"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(99,102,241,0.15) 0%, transparent 70%)',
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-indigo-700/20 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">🏛️</span>
          <h3 className="text-sm font-semibold text-indigo-400">會議室</h3>
          <span className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10px] text-indigo-300">
            {agents.length} 位參與中
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-[10px] text-indigo-400/70">進行中</span>
        </div>
      </div>

      {/* Conference table + agent seats */}
      <div className="relative px-4 py-3">
        {/* 會議桌 */}
        <div className="meeting-table relative mx-auto flex items-center justify-center">
          {/* Table shape */}
          <div className="absolute inset-x-4 inset-y-2 rounded-2xl bg-slate-700/25 border border-slate-600/20" />

          {/* Agents around the table */}
          <div className="relative z-10 flex flex-wrap items-center justify-center gap-3 px-6 py-3">
            {agents.map((agent) => (
              <div key={agent.id} className="flex flex-col items-center gap-0.5">
                <AgentAvatar
                  agent={agent}
                  isSelected={selectedAgent?.id === agent.id}
                  onSelect={onSelectAgent}
                  compact
                />
                <span className="max-w-[3.5rem] truncate text-[9px] text-slate-400">
                  {agent.displayName}
                </span>
                {agent.progress !== undefined && (
                  <div className="h-0.5 w-8 overflow-hidden rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-emerald-400 transition-all duration-700"
                      style={{ width: `${agent.progress}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function OfficeFloorMap({
  rooms,
  selectedAgent,
  onSelectAgent,
}: OfficeFloorMapProps) {
  // 收集所有有任務的代理（working / waiting / completed 且有 currentTask）
  const allAgents = rooms.flatMap((r) => r.agents)
  const meetingAgents = allAgents.filter(
    (a) => a.status === 'working' || a.status === 'waiting'
  )
  const meetingAgentIds = new Set(meetingAgents.map((a) => a.id))

  const totalWorking = allAgents.filter((a) => a.status === 'working').length
  const totalAgents = allAgents.length

  return (
    <div className="office-floor h-full overflow-y-auto p-4">
      <div className="relative mx-auto max-w-7xl">
        {/* Building outline */}
        <div className="rounded-2xl border border-slate-700/30 bg-slate-900/50 p-3 shadow-inner">
          {/* Floor label */}
          <div className="mb-3 flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <div className="h-5 w-1 rounded-full bg-indigo-500/60" />
              <span className="text-xs font-medium tracking-wide text-slate-400">
                WINDAI LAB — 3F 研究樓層
              </span>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-slate-500">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400/60" /> 工作中 {totalWorking}
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-slate-500/60" /> 待命 {totalAgents - totalWorking}
              </span>
            </div>
          </div>

          {/* Meeting Room — 會議室在最上方 */}
          <div className="mb-3">
            <MeetingRoom
              agents={meetingAgents}
              selectedAgent={selectedAgent}
              onSelectAgent={onSelectAgent}
            />
          </div>

          {/* Corridor between meeting room and offices */}
          <div className="mb-3 flex items-center justify-center gap-3">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent" />
            <span className="text-[10px] text-slate-600">▼ 各研究室 ▼</span>
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent" />
          </div>

          {/* Room grid */}
          <div className="grid gap-3 md:grid-cols-3 md:grid-rows-2">
            {rooms.map((room) => (
              <RoomSection
                key={room.id}
                room={room}
                selectedAgent={selectedAgent}
                onSelectAgent={onSelectAgent}
                meetingAgentIds={meetingAgentIds}
              />
            ))}
          </div>

          {/* Exit */}
          <div className="mt-3 flex items-center justify-center gap-4 py-1">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/40 to-transparent" />
            <span className="text-[10px] text-slate-600">🚪 出入口</span>
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/40 to-transparent" />
          </div>
        </div>
      </div>
    </div>
  )
}
