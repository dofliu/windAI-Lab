import { Agent, OfficeRoom } from '../types/agent'
import { tierColors } from '../utils/mockData'
import AgentAvatar from './AgentAvatar'

interface OfficeFloorMapProps {
  rooms: OfficeRoom[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
}

/** Room config: decoration & layout hints */
const roomMeta: Record<string, { label: string; deco: string[] }> = {
  'room-leadership': {
    label: '指揮中心',
    deco: ['🪴', '☕'],
  },
  'room-data': {
    label: '資料工程室',
    deco: ['🖥️', '📊'],
  },
  'room-ai-ml': {
    label: '模型實驗室',
    deco: ['🧪', '⚡'],
  },
  'room-domain': {
    label: '領域知識庫',
    deco: ['🌬️', '📐'],
  },
  'room-engineering': {
    label: '軟體工程室',
    deco: ['💻', '🔧'],
  },
  'room-research': {
    label: '研究室',
    deco: ['📖', '✏️'],
  },
}

function RoomSection({
  room,
  selectedAgent,
  onSelectAgent,
}: {
  room: OfficeRoom
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
}) {
  const colors = tierColors[room.tier] ?? tierColors['leadership']
  const meta = roomMeta[room.id] ?? { label: room.name, deco: [] }
  const workingCount = room.agents.filter((a) => a.status === 'working').length

  return (
    <div className={`office-room ${colors.bg} relative overflow-hidden border ${colors.border}`}>
      {/* Room walls — thick inner border effect */}
      <div className="absolute inset-0 rounded-xl border-2 border-slate-600/20 pointer-events-none" />

      {/* Room header — like a door sign */}
      <div className="room-header flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">{room.icon}</span>
          <h3 className={`text-sm font-semibold ${colors.accent}`}>
            {meta.label}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {workingCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {workingCount} 位工作中
            </span>
          )}
          <span className="text-[10px] text-slate-500">
            {room.agents.length} 人
          </span>
        </div>
      </div>

      {/* Door indicator */}
      <div className="absolute left-1/2 top-0 -translate-x-1/2">
        <div className="h-1 w-8 rounded-b bg-slate-500/30" />
      </div>

      {/* Desks area — agents sit here */}
      <div className="desks-area flex flex-wrap justify-center gap-3 px-3 pb-3 pt-1">
        {room.agents.map((agent) => (
          <AgentAvatar
            key={agent.id}
            agent={agent}
            isSelected={selectedAgent?.id === agent.id}
            onSelect={onSelectAgent}
            size={room.agents.length > 8 ? 'sm' : 'md'}
          />
        ))}
      </div>

      {/* Room decorations — plants, coffee, etc */}
      {meta.deco.length > 0 && (
        <div className="absolute bottom-2 right-3 flex gap-1.5 opacity-30">
          {meta.deco.map((d, i) => (
            <span key={i} className="text-xs">{d}</span>
          ))}
        </div>
      )}

      {/* Floor texture hint */}
      <div className="absolute inset-0 rounded-xl pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '16px 16px',
        }}
      />
    </div>
  )
}

export default function OfficeFloorMap({
  rooms,
  selectedAgent,
  onSelectAgent,
}: OfficeFloorMapProps) {
  const totalWorking = rooms.reduce(
    (sum, r) => sum + r.agents.filter((a) => a.status === 'working').length,
    0
  )
  const totalAgents = rooms.reduce((sum, r) => sum + r.agents.length, 0)

  return (
    <div className="office-floor h-full overflow-y-auto p-4">
      {/* Floor plan container with subtle grid background */}
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

          {/* Room grid — 3 columns, 2 rows mimicking office layout */}
          <div className="grid gap-3 md:grid-cols-3 md:grid-rows-2">
            {/* Row 1: Leadership (wide) | Data Eng | AI/ML */}
            {rooms.map((room) => (
              <RoomSection
                key={room.id}
                room={room}
                selectedAgent={selectedAgent}
                onSelectAgent={onSelectAgent}
              />
            ))}
          </div>

          {/* Hallway / corridor decoration */}
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
