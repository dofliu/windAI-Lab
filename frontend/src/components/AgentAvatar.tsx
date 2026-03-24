import { useState } from 'react'
import { Agent } from '../types/agent'

interface AgentAvatarProps {
  agent: Agent
  isSelected: boolean
  onSelect: (agent: Agent) => void
  size?: 'sm' | 'md'
}

const statusRing: Record<string, string> = {
  idle: 'ring-slate-500/50',
  working: 'ring-emerald-400 animate-pulse-ring',
  waiting: 'ring-amber-400 animate-blink-ring',
  completed: 'ring-blue-400',
  error: 'ring-red-500 animate-pulse-ring',
}

const statusGlow: Record<string, string> = {
  idle: '',
  working: 'shadow-[0_0_12px_rgba(52,211,153,0.4)]',
  waiting: 'shadow-[0_0_10px_rgba(251,191,36,0.3)]',
  completed: 'shadow-[0_0_10px_rgba(96,165,250,0.3)]',
  error: 'shadow-[0_0_12px_rgba(239,68,68,0.4)]',
}

export default function AgentAvatar({ agent, isSelected, onSelect, size = 'md' }: AgentAvatarProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  const dim = size === 'sm' ? 'h-9 w-9' : 'h-11 w-11'
  const textSize = size === 'sm' ? 'text-sm' : 'text-lg'
  const ringWidth = isSelected ? 'ring-[3px]' : 'ring-2'

  return (
    <div
      className="desk-slot group relative flex flex-col items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Desk surface */}
      <div className="desk-surface mb-1 rounded-md bg-slate-700/40 px-1 pb-1 pt-3">
        {/* Avatar circle */}
        <button
          onClick={() => onSelect(agent)}
          className={`relative flex items-center justify-center rounded-full
            ${dim} ${ringWidth} ${statusRing[agent.status]} ${statusGlow[agent.status]}
            bg-slate-800 transition-all duration-300 hover:scale-110
            ${isSelected ? 'scale-110 brightness-125' : ''}
          `}
        >
          <span className={`${textSize} leading-none`}>{agent.icon}</span>

          {/* Working indicator - small typing dots */}
          {agent.status === 'working' && (
            <span className="absolute -bottom-1 left-1/2 flex -translate-x-1/2 gap-0.5">
              <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '0ms' }} />
              <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '150ms' }} />
              <span className="h-1 w-1 rounded-full bg-emerald-400 animate-bounce-dot" style={{ animationDelay: '300ms' }} />
            </span>
          )}
        </button>

        {/* Monitor / screen on desk */}
        <div className={`mt-1 h-1.5 w-8 rounded-sm mx-auto ${
          agent.status === 'working' ? 'bg-emerald-500/30 animate-screen-flicker' :
          agent.status === 'idle' ? 'bg-slate-600/30' :
          agent.status === 'error' ? 'bg-red-500/30' :
          'bg-blue-500/20'
        }`} />
      </div>

      {/* Name label */}
      <span className="mt-0.5 max-w-[4.5rem] truncate text-center text-[10px] leading-tight text-slate-400 group-hover:text-slate-200">
        {agent.displayName}
      </span>

      {/* Progress bar under name */}
      {agent.status === 'working' && agent.progress !== undefined && (
        <div className="mt-0.5 h-0.5 w-10 overflow-hidden rounded-full bg-slate-700">
          <div
            className="h-full rounded-full bg-emerald-400 transition-all duration-700"
            style={{ width: `${agent.progress}%` }}
          />
        </div>
      )}

      {/* Hover tooltip */}
      {showTooltip && (
        <div className="agent-tooltip absolute -top-2 left-1/2 z-50 -translate-x-1/2 -translate-y-full">
          <div className="rounded-lg border border-slate-600/80 bg-slate-800/95 px-3 py-2 shadow-xl backdrop-blur-sm whitespace-nowrap">
            <div className="flex items-center gap-2">
              <span className="text-base">{agent.icon}</span>
              <div>
                <p className="text-xs font-semibold text-slate-100">{agent.displayName}</p>
                <p className="text-[10px] text-slate-500">{agent.name}</p>
              </div>
            </div>
            {agent.currentTask && (
              <p className="mt-1.5 max-w-[200px] truncate text-[10px] text-slate-300">
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
      )}
    </div>
  )
}
