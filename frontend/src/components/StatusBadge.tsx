import { AgentStatus } from '../types/agent'
import { useTheme, getStatusColor } from '../themes'

const statusLabels: Record<AgentStatus, string> = {
  idle: '待命中',
  working: '工作中',
  waiting: '等待確認',
  completed: '已完成',
  error: '錯誤',
}

const statusAnimations: Record<AgentStatus, string> = {
  idle: '',
  working: 'animate-pulse-slow',
  waiting: 'animate-blink',
  completed: '',
  error: '',
}

interface StatusBadgeProps {
  status: AgentStatus
  showLabel?: boolean
  size?: 'sm' | 'md'
}

export default function StatusBadge({
  status,
  showLabel = true,
  size = 'sm',
}: StatusBadgeProps) {
  const { theme } = useTheme()
  const colors = getStatusColor(theme, status)
  const dotSize = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3'
  const animation = statusAnimations[status]

  if (!showLabel) {
    return (
      <span
        className={`status-dot ${dotSize} ${animation}`}
        style={{ backgroundColor: colors.dot }}
      />
    )
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: colors.bg, color: colors.text }}
    >
      <span
        className={`status-dot ${dotSize} ${animation}`}
        style={{ backgroundColor: colors.dot }}
      />
      {statusLabels[status]}
    </span>
  )
}
