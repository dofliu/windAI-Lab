import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Agent, OfficeRoom, SpeechBubble } from '../types/agent'
import PixelCharacter from './PixelCharacter'

/* ================================================================
   Layout configuration — 所有座標為百分比 (0-100)
   ================================================================ */

interface RoomDef {
  x: number; y: number; w: number; h: number
  label: string; icon: string
  floor: string; border: string; labelColor: string
}

const MEETING: RoomDef = {
  x: 11, y: 8, w: 78, h: 14,
  label: '會議室', icon: '🏛️',
  floor: 'rgba(99,102,241,0.06)',
  border: 'rgba(99,102,241,0.25)',
  labelColor: '#818cf8',
}

const BOSS_ROOM: RoomDef = {
  x: 1, y: 8, w: 9, h: 14,
  label: '私密室', icon: '🔒',
  floor: 'rgba(236,72,153,0.08)',
  border: 'rgba(236,72,153,0.3)',
  labelColor: '#f472b6',
}

const TEA_ROOM: RoomDef = {
  x: 90, y: 8, w: 9, h: 14,
  label: '茶水間', icon: '☕',
  floor: 'rgba(251,191,36,0.06)',
  border: 'rgba(251,191,36,0.25)',
  labelColor: '#fbbf24',
}

const ROOMS: Record<string, RoomDef> = {
  leadership:  { x: 1, y: 27, w: 31, h: 28, label: '指揮中心',   icon: '🏛️', floor: 'rgba(245,158,11,0.05)',  border: 'rgba(245,158,11,0.22)', labelColor: '#fbbf24' },
  data:        { x: 35, y: 27, w: 30, h: 28, label: '資料工程室', icon: '🗃️', floor: 'rgba(16,185,129,0.05)',  border: 'rgba(16,185,129,0.22)', labelColor: '#34d399' },
  'ai-ml':     { x: 68, y: 27, w: 31, h: 28, label: '模型實驗室', icon: '🧠', floor: 'rgba(139,92,246,0.05)',  border: 'rgba(139,92,246,0.22)', labelColor: '#a78bfa' },
  domain:      { x: 1, y: 58, w: 31, h: 28, label: '領域知識庫', icon: '🌬️', floor: 'rgba(236,72,153,0.05)',  border: 'rgba(236,72,153,0.22)', labelColor: '#f472b6' },
  engineering: { x: 35, y: 58, w: 30, h: 28, label: '軟體工程室', icon: '💻', floor: 'rgba(249,115,22,0.05)',  border: 'rgba(249,115,22,0.22)', labelColor: '#fb923c' },
  research:    { x: 68, y: 58, w: 31, h: 28, label: '研究室',     icon: '📖', floor: 'rgba(6,182,212,0.05)',   border: 'rgba(6,182,212,0.22)',  labelColor: '#22d3ee' },
}

/* ── Position helpers ── */

function deskGrid(room: RoomDef, count: number) {
  if (count === 0) return []
  // padX: horizontal margin from room edges
  // topPad: space for room label + character head above anchor
  // botPad: space for nametag + progress bar below anchor (feet)
  const padX = 3, topPad = 10, botPad = 8
  const cols = Math.min(count, count <= 4 ? count : Math.ceil(Math.sqrt(count * 2)))
  const rows = Math.ceil(count / cols)
  const aw = room.w - padX * 2
  const ah = room.h - topPad - botPad
  return Array.from({ length: count }, (_, i) => ({
    x: room.x + padX + (cols > 1 ? (i % cols) * aw / (cols - 1) : aw / 2),
    y: room.y + topPad + (rows > 1 ? Math.floor(i / cols) * ah / (rows - 1) : ah / 2),
  }))
}

/** 根據參與人數動態產生會議室座位（橢圓排列），保證每個人有獨立座位 */
function meetingSeats(count: number) {
  if (count === 0) return []
  const cx = MEETING.x + MEETING.w / 2
  const cy = MEETING.y + MEETING.h / 2 + 1
  const rx = MEETING.w * 0.32
  const ry = MEETING.h * 0.2
  return Array.from({ length: count }, (_, i) => ({
    x: cx + Math.cos((i / count) * Math.PI * 2 - Math.PI / 2) * rx,
    y: cy + Math.sin((i / count) * Math.PI * 2 - Math.PI / 2) * ry,
  }))
}

/* ── Room furniture decorations ── */
const ROOM_DECO: Record<string, Array<{ emoji: string; x: number; y: number }>> = {
  leadership:  [{ emoji: '🪴', x: 90, y: 85 }, { emoji: '☕', x: 10, y: 85 }],
  data:        [{ emoji: '🖥️', x: 92, y: 30 }, { emoji: '📊', x: 92, y: 60 }],
  'ai-ml':     [{ emoji: '🧪', x: 92, y: 85 }, { emoji: '⚡', x: 8, y: 85 }],
  domain:      [{ emoji: '📐', x: 92, y: 85 }, { emoji: '🌬️', x: 8, y: 85 }],
  engineering: [{ emoji: '🔧', x: 92, y: 85 }, { emoji: '💻', x: 8, y: 85 }],
  research:    [{ emoji: '📖', x: 92, y: 85 }, { emoji: '✏️', x: 8, y: 85 }],
}

/* ================================================================
   OfficeWorld component
   ================================================================ */

interface Props {
  rooms: OfficeRoom[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
  speechBubbles?: SpeechBubble[]
}

export default function OfficeWorld({ rooms, selectedAgent, onSelectAgent, speechBubbles = [] }: Props) {
  const allAgents = useMemo(() => rooms.flatMap((r) => r.agents), [rooms])

  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [walkingIds, setWalkingIds] = useState<Set<string>>(new Set())
  const [mounted, setMounted] = useState(false)
  const prevStatusRef = useRef<Map<string, string>>(new Map())
  const walkTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  // Enable CSS transitions after initial render
  useEffect(() => {
    requestAnimationFrame(() => setMounted(true))
  }, [])

  /* ── Compute positions ── */
  const { positions, meetingIds, specialIds } = useMemo(() => {
    const pos = new Map<string, { x: number; y: number }>()
    const mIds = new Set<string>()
    const sIds = new Set<string>()

    // 1. Special rooms (boss-room, tea-room) — highest priority
    const inBoss = allAgents.filter((a) => a.location === 'boss-room')
    inBoss.forEach((agent, i) => {
      const cx = BOSS_ROOM.x + BOSS_ROOM.w / 2
      const cy = BOSS_ROOM.y + BOSS_ROOM.h * 0.55
      pos.set(agent.id, { x: cx + (i - (inBoss.length - 1) / 2) * 3.5, y: cy })
      sIds.add(agent.id)
    })

    const inTea = allAgents.filter((a) => a.location === 'tea-room')
    inTea.forEach((agent, i) => {
      const cx = TEA_ROOM.x + TEA_ROOM.w / 2
      const cy = TEA_ROOM.y + TEA_ROOM.h * 0.55
      pos.set(agent.id, { x: cx + (i - (inTea.length - 1) / 2) * 3, y: cy })
      sIds.add(agent.id)
    })

    // 2. Meeting room agents — working/waiting without special location
    const inMeeting = allAgents.filter(
      (a) => (a.status === 'working' || a.status === 'waiting') && !sIds.has(a.id),
    )
    const seats = meetingSeats(inMeeting.length)
    inMeeting.forEach((agent, i) => {
      pos.set(agent.id, seats[i])
      mIds.add(agent.id)
    })

    // Desk agents
    rooms.forEach((room) => {
      const def = ROOMS[room.tier]
      if (!def) return
      const desks = deskGrid(def, room.agents.length)
      room.agents.forEach((agent, i) => {
        if (!pos.has(agent.id) && i < desks.length) {
          pos.set(agent.id, desks[i])
        }
      })
    })

    return { positions: pos, meetingIds: mIds, specialIds: sIds }
  }, [allAgents, rooms])

  /* ── Start walk animation for a specific agent ── */
  const startWalking = useCallback((agentId: string) => {
    // Clear any existing timer for this agent
    const existing = walkTimers.current.get(agentId)
    if (existing) clearTimeout(existing)

    setWalkingIds((prev) => new Set(prev).add(agentId))

    // Stop walking after CSS transition completes
    walkTimers.current.set(agentId, setTimeout(() => {
      setWalkingIds((prev) => {
        const next = new Set(prev)
        next.delete(agentId)
        return next
      })
      walkTimers.current.delete(agentId)
    }, 2200))
  }, [])

  /* ── Detect movement (status/location change → room transition) ── */
  useEffect(() => {
    allAgents.forEach((agent) => {
      // Encode current position category as a string for comparison
      const locKey = agent.location ?? (
        agent.status === 'working' || agent.status === 'waiting' ? 'meeting' : 'desk'
      )
      const prevKey = prevStatusRef.current.get(agent.id)
      if (prevKey && prevKey !== locKey) {
        startWalking(agent.id)
      }
    })

    const newMap = new Map<string, string>()
    allAgents.forEach((a) => {
      const key = a.location ?? (
        a.status === 'working' || a.status === 'waiting' ? 'meeting' : 'desk'
      )
      newMap.set(a.id, key)
    })
    prevStatusRef.current = newMap
  }, [allAgents, startWalking])

  // Cleanup all walk timers on unmount
  useEffect(() => {
    return () => {
      walkTimers.current.forEach((t) => clearTimeout(t))
    }
  }, [])

  const meetingCount = meetingIds.size

  const bossOccupied = allAgents.some((a) => a.location === 'boss-room')
  const teaOccupied = allAgents.some((a) => a.location === 'tea-room')

  return (
    <div className="office-world">
      {/* ════ Boss Room (hidden feature) ════ */}
      <RoomBox room={BOSS_ROOM} count={allAgents.filter((a) => a.location === 'boss-room').length} />
      {bossOccupied && (
        <div className="pixel-hearts" style={{
          position: 'absolute',
          left: `${BOSS_ROOM.x + BOSS_ROOM.w / 2}%`,
          top: `${BOSS_ROOM.y - 1}%`,
          transform: 'translate(-50%, -50%)',
        }}>
          <span>❤️</span><span>💕</span><span>❤️</span>
        </div>
      )}

      {/* ════ Tea Room ════ */}
      <RoomBox room={TEA_ROOM} count={allAgents.filter((a) => a.location === 'tea-room').length} />
      {teaOccupied && (
        <div className="pixel-tea-activity" style={{
          position: 'absolute',
          left: `${TEA_ROOM.x + TEA_ROOM.w / 2}%`,
          top: `${TEA_ROOM.y - 1}%`,
          transform: 'translate(-50%, -50%)',
        }}>
          <span>☕</span><span>🎮</span><span>🍪</span>
        </div>
      )}

      {/* ════ Meeting Room ════ */}
      <RoomBox room={MEETING} count={meetingCount} extra={meetingCount > 0 ? '進行中' : '空閒'} />

      {/* Conference table */}
      <div
        className="pixel-conf-table"
        style={{
          left: `${MEETING.x + MEETING.w * 0.28}%`,
          top: `${MEETING.y + MEETING.h * 0.3}%`,
          width: `${MEETING.w * 0.44}%`,
          height: `${MEETING.h * 0.4}%`,
        }}
      />

      {/* ════ Corridor ════ */}
      <div
        className="absolute flex items-center justify-center"
        style={{ left: '5%', right: '5%', top: '23%', height: '3%' }}
      >
        <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-700/25 to-transparent" />
        <span className="absolute text-[9px] text-slate-600 bg-slate-900/80 px-2">▼ 各研究室 ▼</span>
      </div>

      {/* ════ Office Rooms ════ */}
      {Object.entries(ROOMS).map(([tier, def]) => {
        const room = rooms.find((r) => r.tier === tier)
        const inM = room ? room.agents.filter((a) => meetingIds.has(a.id)).length : 0
        return (
          <RoomBox key={tier} room={def} count={room?.agents.length ?? 0} inMeeting={inM} />
        )
      })}

      {/* ════ Room furniture decorations ════ */}
      {Object.entries(ROOMS).map(([tier, def]) => (
        <div key={`deco-${tier}`}>
          {(ROOM_DECO[tier] ?? []).map((d, i) => (
            <span
              key={i}
              className="absolute text-[10px] opacity-20 pointer-events-none select-none"
              style={{
                left: `${def.x + d.x * def.w / 100}%`,
                top: `${def.y + d.y * def.h / 100}%`,
              }}
            >
              {d.emoji}
            </span>
          ))}
        </div>
      ))}

      {/* ════ Desks (furniture) ════ */}
      {rooms.flatMap((room) => {
        const def = ROOMS[room.tier]
        if (!def) return []
        const desks = deskGrid(def, room.agents.length)
        return desks.map((pos, i) => {
          const agent = room.agents[i]
          const empty = agent && (meetingIds.has(agent.id) || specialIds.has(agent.id))
          return (
            <div
              key={`desk-${room.tier}-${i}`}
              className="pixel-desk"
              style={{
                left: `calc(${pos.x}% - 10px)`,
                top: `calc(${pos.y}% + 18px)`,
                opacity: empty ? 0.2 : 0.5,
              }}
            >
              {/* Monitor on desk */}
              <div className={`pixel-monitor ${
                agent?.status === 'working' && !empty ? 'pixel-monitor-on' : ''
              }`} />
            </div>
          )
        })
      })}

      {/* ════ Empty desk markers (agent in meeting) ════ */}
      {rooms.flatMap((room) => {
        const def = ROOMS[room.tier]
        if (!def) return []
        const desks = deskGrid(def, room.agents.length)
        return desks.map((pos, i) => {
          const agent = room.agents[i]
          if (!agent || (!meetingIds.has(agent.id) && !specialIds.has(agent.id))) return null
          return (
            <div
              key={`empty-${room.tier}-${i}`}
              className="pixel-empty-seat"
              style={{
                left: `${pos.x}%`,
                top: `${pos.y}%`,
              }}
            >
              <span className="text-[8px] text-slate-600 whitespace-nowrap">{agent.location === 'boss-room' ? '私密中' : agent.location === 'tea-room' ? '休息中' : '會議中'}</span>
            </div>
          )
        })
      })}

      {/* ════ Agents (pixel characters) ════ */}
      {allAgents.map((agent) => {
        const pos = positions.get(agent.id)
        if (!pos) return null
        const isWalking = walkingIds.has(agent.id)
        const isSelected = selectedAgent?.id === agent.id
        const isHovered = hoveredId === agent.id

        return (
          <div
            key={agent.id}
            className={`pixel-agent ${isSelected ? 'pixel-agent-selected' : ''} ${isWalking ? 'pixel-agent-walking' : ''}`}
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              transition: mounted ? 'left 2s ease-in-out, top 2s ease-in-out' : 'none',
              zIndex: speechBubbles.some((b) => b.agentId === agent.id) ? 50 : isHovered || isSelected ? 30 : 10,
            }}
            onClick={() => onSelectAgent(agent)}
            onMouseEnter={() => setHoveredId(agent.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <PixelCharacter
              agentId={agent.id}
              tier={agent.tier}
              status={agent.status}
              isWalking={isWalking}
              size={20}
            />
            <span className="pixel-nametag">{agent.displayName}</span>

            {/* Progress bar */}
            {agent.status === 'working' && agent.progress !== undefined && (
              <div className="pixel-progress">
                <div className="pixel-progress-fill" style={{ width: `${agent.progress}%` }} />
              </div>
            )}

            {/* Speech bubble — flip below agent when near top to avoid clipping */}
            {speechBubbles.find((b) => b.agentId === agent.id) && (
              <div className={pos.y < 22 ? 'pixel-speech-bubble-below' : 'pixel-speech-bubble'}>
                {speechBubbles.find((b) => b.agentId === agent.id)!.text}
              </div>
            )}

            {/* Hover tooltip (only when no speech bubble) */}
            {isHovered && !speechBubbles.find((b) => b.agentId === agent.id) && (
              <div className="pixel-tooltip" style={pos.y < 22 ? { bottom: 'auto', top: 'calc(100% + 8px)' } : undefined}>
                <p className="font-semibold text-slate-100">{agent.displayName}</p>
                <p className="text-slate-500">{agent.name}</p>
                {agent.currentTask && (
                  <p className="mt-1 text-slate-300 max-w-[200px] truncate">{agent.currentTask}</p>
                )}
                {agent.progress !== undefined && agent.status === 'working' && (
                  <div className="mt-1 flex items-center gap-1">
                    <div className="h-1 flex-1 rounded-full bg-slate-700 overflow-hidden">
                      <div className="h-full bg-emerald-400" style={{ width: `${agent.progress}%` }} />
                    </div>
                    <span className="text-emerald-400">{agent.progress}%</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* ════ Exit ════ */}
      <div className="absolute bottom-1 left-0 right-0 flex items-center justify-center gap-3 py-1">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent" />
        <span className="text-[9px] text-slate-600">🚪 出入口</span>
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent" />
      </div>
    </div>
  )
}

/* ── Room box background ── */
function RoomBox({
  room,
  count,
  inMeeting = 0,
  extra,
}: {
  room: RoomDef
  count: number
  inMeeting?: number
  extra?: string
}) {
  return (
    <div
      className="pixel-room"
      style={{
        left: `${room.x}%`,
        top: `${room.y}%`,
        width: `${room.w}%`,
        height: `${room.h}%`,
        backgroundColor: room.floor,
        borderColor: room.border,
      }}
    >
      {/* Label */}
      <div className="pixel-room-label" style={{ color: room.labelColor }}>
        <span className="mr-1">{room.icon}</span>
        <span className="font-semibold">{room.label}</span>
        {inMeeting > 0 && (
          <span className="ml-2 text-[8px] text-indigo-400/60">{inMeeting} 在會議室</span>
        )}
        {extra && (
          <span className="ml-2 text-[8px] opacity-60">{extra}</span>
        )}
        <span className="ml-auto text-[8px] opacity-40">{count} 人</span>
      </div>

      {/* Pixel floor tile pattern */}
      <div
        className="absolute inset-0 rounded-xl pointer-events-none"
        style={{
          opacity: 0.03,
          backgroundImage: `
            linear-gradient(90deg, white 1px, transparent 1px),
            linear-gradient(white 1px, transparent 1px)
          `,
          backgroundSize: '8px 8px',
        }}
      />
    </div>
  )
}
