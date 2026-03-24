import { useState } from 'react'
import { Agent } from '../types/agent'
import AvatarSVG from './AvatarSVG'

interface AgentAvatarProps {
  agent: Agent
  isSelected: boolean
  onSelect: (agent: Agent) => void
  size?: 'sm' | 'md'
  /** 是否顯示為會議室中的小頭像 */
  compact?: boolean
}

const statusRing: Record<string, string> = {
  idle: 'ring-slate-500/40',
  working: 'ring-emerald-400',
  waiting: 'ring-amber-400 animate-blink-ring',
  completed: 'ring-blue-400',
  error: 'ring-red-500',
}

export default function AgentAvatar({
  agent,
  isSelected,
  onSelect,
  size = 'md',
  compact = false,
}: AgentAvatarProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  const avatarPx = compact ? 28 : size === 'sm' ? 36 : 44
  const ringWidth = isSelected ? 'ring-[3px]' : 'ring-2'

  const isWorking = agent.status === 'working'
  const isWaiting = agent.status === 'waiting'
  const isError = agent.status === 'error'

  // 工作中底色閃爍 class
  const workingBg = isWorking
    ? 'agent-working-glow'
    : isWaiting
      ? 'agent-waiting-glow'
      : isError
        ? 'agent-error-glow'
        : ''

  if (compact) {
    // 會議室中的迷你頭像
    return (
      <div
        className="group relative"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <button
          onClick={() => onSelect(agent)}
          className={`relative overflow-hidden rounded-full ${ringWidth} ${statusRing[agent.status]}
            transition-all duration-300 hover:scale-110 ${workingBg}
            ${isSelected ? 'scale-110 ring-[3px] ring-indigo-400' : ''}
          `}
        >
          <AvatarSVG
            agentId={agent.id}
            tier={agent.tier}
            displayName={agent.displayName}
            size={avatarPx}
          />
          {/* Working pulse overlay */}
          {isWorking && (
            <span className="absolute inset-0 rounded-full bg-emerald-400/20 animate-ping-slow" />
          )}
        </button>

        {/* Tooltip */}
        {showTooltip && <AvatarTooltip agent={agent} />}
      </div>
    )
  }

  return (
    <div
      className="desk-slot group relative flex flex-col items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Desk surface */}
      <div className={`desk-surface mb-1 rounded-lg px-1.5 pb-1.5 pt-3 transition-all duration-500
        ${isWorking ? 'bg-emerald-900/30 agent-desk-working' : ''}
        ${isWaiting ? 'bg-amber-900/20' : ''}
        ${isError ? 'bg-red-900/20' : ''}
        ${!isWorking && !isWaiting && !isError ? 'bg-slate-700/30' : ''}
      `}>
        {/* Avatar circle */}
        <button
          onClick={() => onSelect(agent)}
          className={`relative overflow-hidden rounded-full
            ${ringWidth} ${statusRing[agent.status]}
            transition-all duration-300 hover:scale-110
            ${workingBg}
            ${isSelected ? 'scale-110 ring-[3px] ring-indigo-400' : ''}
          `}
        >
          <AvatarSVG
            agentId={agent.id}
            tier={agent.tier}
            displayName={agent.displayName}
            size={avatarPx}
          />

          {/* Working pulse overlay */}
          {isWorking && (
            <span className="absolute inset-0 rounded-full bg-emerald-400/15 animate-ping-slow" />
          )}
        </button>

        {/* Working indicator - typing dots */}
        {isWorking && (
          <span className="mt-1 flex justify-center gap-0.5">
            <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '0ms' }} />
            <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '150ms' }} />
            <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '300ms' }} />
          </span>
        )}

        {/* Monitor / screen on desk */}
        {!isWorking && (
          <div className={`mt-1 h-1.5 w-8 rounded-sm mx-auto ${
            agent.status === 'idle' ? 'bg-slate-600/30' :
            agent.status === 'error' ? 'bg-red-500/30' :
            agent.status === 'waiting' ? 'bg-amber-500/20' :
            'bg-blue-500/20'
          }`} />
        )}
      </div>

      {/* Name label */}
      <span className="mt-0.5 max-w-[4.5rem] truncate text-center text-[10px] leading-tight text-slate-400 group-hover:text-slate-200 transition-colors">
        {agent.displayName}
      </span>

      {/* Progress bar under name */}
      {isWorking && agent.progress !== undefined && (
        <div className="mt-0.5 h-1 w-12 overflow-hidden rounded-full bg-slate-700">
          <div
            className="h-full rounded-full bg-emerald-400 transition-all duration-700"
            style={{ width: `${agent.progress}%` }}
          />
        </div>
      )}

      {/* Hover tooltip */}
      {showTooltip && <AvatarTooltip agent={agent} />}
    </div>
  )
}

function AvatarTooltip({ agent }: { agent: Agent }) {
  return (
    <div className="agent-tooltip absolute -top-2 left-1/2 z-50 -translate-x-1/2 -translate-y-full pointer-events-none">
      <div className="rounded-lg border border-slate-600/80 bg-slate-800/95 px-3 py-2 shadow-xl backdrop-blur-sm whitespace-nowrap">
        <div className="flex items-center gap-2">
          <AvatarSVG
            agentId={agent.id}
            tier={agent.tier}
            displayName={agent.displayName}
            size={24}
          />
          <div>
            <p className="text-xs font-semibold text-slate-100">{agent.displayName}</p>
            <p className="text-[10px] text-slate-500">{agent.name}</p>
          </div>
        </div>
        {agent.currentTask && (
          <p className="mt-1.5 max-w-[220px] truncate text-[10px] text-slate-300">
            {agent.currentTask}
          </p>
        )}
        {agent.progress !== undefined && agent.status === 'working' && (
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-700">
              <div className="h-full bg-emerald-400" style={{ width: `${agent.progress}%` }} />
            </div>
            <span className="text-[10px] text-emerald-400">{agent.progress}%</span>
          </div>
        )}
        {/* Tooltip arrow */}
        <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-slate-600/80" />
      </div>
    </div>
  )
}
