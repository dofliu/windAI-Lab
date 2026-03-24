import { AgentStatus } from '../types/agent'

const statusConfig: Record<
  AgentStatus,
  { label: string; dotClass: string; badgeClass: string }
> = {
  idle: {
    label: '待命中',
    dotClass: 'bg-slate-400',
    badgeClass: 'bg-slate-700/60 text-slate-300',
  },
  working: {
    label: '工作中',
    dotClass: 'bg-emerald-400 animate-pulse-slow',
    badgeClass: 'bg-emerald-900/50 text-emerald-300',
  },
  waiting: {
    label: '等待確認',
    dotClass: 'bg-amber-400 animate-blink',
    badgeClass: 'bg-amber-900/50 text-amber-300',
  },
  completed: {
    label: '已完成',
    dotClass: 'bg-blue-400',
    badgeClass: 'bg-blue-900/50 text-blue-300',
  },
  error: {
    label: '錯誤',
    dotClass: 'bg-red-500',
    badgeClass: 'bg-red-900/50 text-red-300',
  },
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
  const config = statusConfig[status]
  const dotSize = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3'

  if (!showLabel) {
    return <span className={`status-dot ${dotSize} ${config.dotClass}`} />
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.badgeClass}`}
    >
      <span className={`status-dot ${dotSize} ${config.dotClass}`} />
      {config.label}
    </span>
  )
}
