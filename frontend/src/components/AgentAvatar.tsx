import { useState } from 'react'
import { Agent } from '../types/agent'
import { useTheme, getStatusColor } from '../themes'
import AvatarSVG from './AvatarSVG'

interface AgentAvatarProps {
  agent: Agent
  isSelected: boolean
  onSelect: (agent: Agent) => void
  size?: 'sm' | 'md'
  /** 是否顯示為會議室中的小頭像 */
  compact?: boolean
}

export default function AgentAvatar({
  agent,
  isSelected,
  onSelect,
  size = 'md',
  compact = false,
}: AgentAvatarProps) {
  const { theme } = useTheme()
  const statusColor = getStatusColor(theme, agent.status)
  const [showTooltip, setShowTooltip] = useState(false)

  const avatarPx = compact ? 28 : size === 'sm' ? 36 : 44
  const ringPx = isSelected ? '3px' : '2px'

  const isWorking = agent.status === 'working'
  const isWaiting = agent.status === 'waiting'
  const isError = agent.status === 'error'

  const ringStyle = {
    boxShadow: `0 0 0 ${ringPx} ${statusColor.dot}`,
  }

  if (compact) {
    return (
      <div
        className="group relative"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <button
          onClick={() => onSelect(agent)}
          className="relative overflow-hidden rounded-full transition-all duration-300 hover:scale-110"
          style={isSelected ? { ...ringStyle, boxShadow: `0 0 0 3px ${theme.global.accent}` } : ringStyle}
        >
          <AvatarSVG agentId={agent.id} tier={agent.tier} displayName={agent.displayName} size={avatarPx} />
          {isWorking && (
            <span className="absolute inset-0 rounded-full animate-ping-slow" style={{ backgroundColor: statusColor.dot + '33' }} />
          )}
        </button>
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
      <div
        className="desk-surface mb-1 rounded-lg px-1.5 pb-1.5 pt-3 transition-all duration-500"
        style={{ backgroundColor: isWorking || isWaiting || isError ? statusColor.bg + '4d' : theme.global.border + '4d' }}
      >
        <button
          onClick={() => onSelect(agent)}
          className="relative overflow-hidden rounded-full transition-all duration-300 hover:scale-110"
          style={isSelected ? { ...ringStyle, boxShadow: `0 0 0 3px ${theme.global.accent}` } : ringStyle}
        >
          <AvatarSVG agentId={agent.id} tier={agent.tier} displayName={agent.displayName} size={avatarPx} />
          {isWorking && (
            <span className="absolute inset-0 rounded-full animate-ping-slow" style={{ backgroundColor: statusColor.dot + '26' }} />
          )}
        </button>

        {isWorking && (
          <span className="mt-1 flex justify-center gap-0.5">
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                className="h-1 w-1 rounded-full animate-bounce-dot"
                style={{ backgroundColor: statusColor.dot, animationDelay: `${delay}ms` }}
              />
            ))}
          </span>
        )}

        {!isWorking && (
          <div className="mt-1 h-1.5 w-8 rounded-sm mx-auto" style={{ backgroundColor: statusColor.dot + '33' }} />
        )}
      </div>

      <span
        className="mt-0.5 max-w-[4.5rem] truncate text-center text-[10px] leading-tight transition-colors group-hover:opacity-90"
        style={{ color: theme.global.textSecondary }}
      >
        {agent.displayName}
      </span>

      {isWorking && agent.progress !== undefined && (
        <div className="mt-0.5 h-1 w-12 overflow-hidden rounded-full" style={{ backgroundColor: theme.global.border }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${agent.progress}%`, backgroundColor: statusColor.dot }}
          />
        </div>
      )}

      {showTooltip && <AvatarTooltip agent={agent} />}
    </div>
  )
}

function AvatarTooltip({ agent }: { agent: Agent }) {
  const { theme } = useTheme()
  const sc = getStatusColor(theme, agent.status)

  return (
    <div className="agent-tooltip absolute -top-2 left-1/2 z-50 -translate-x-1/2 -translate-y-full pointer-events-none">
      <div
        className="rounded-lg border px-3 py-2 shadow-xl backdrop-blur-sm whitespace-nowrap"
        style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg + 'f2' }}
      >
        <div className="flex items-center gap-2">
          <AvatarSVG agentId={agent.id} tier={agent.tier} displayName={agent.displayName} size={24} />
          <div>
            <p className="text-xs font-semibold" style={{ color: theme.global.textPrimary }}>{agent.displayName}</p>
            <p className="text-[10px]" style={{ color: theme.global.textMuted }}>{agent.name}</p>
          </div>
        </div>
        {agent.currentTask && (
          <p className="mt-1.5 max-w-[220px] truncate text-[10px]" style={{ color: theme.global.textSecondary }}>
            {agent.currentTask}
          </p>
        )}
        {agent.progress !== undefined && agent.status === 'working' && (
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: theme.global.border }}>
              <div className="h-full" style={{ width: `${agent.progress}%`, backgroundColor: sc.dot }} />
            </div>
            <span className="text-[10px]" style={{ color: sc.text }}>{agent.progress}%</span>
          </div>
        )}
        <div
          className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent"
          style={{ borderTopColor: theme.global.border }}
        />
      </div>
    </div>
  )
}
