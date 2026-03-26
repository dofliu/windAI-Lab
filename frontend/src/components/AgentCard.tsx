import { Agent } from '../types/agent'
import { useTheme, getStatusColor } from '../themes'
import StatusBadge from './StatusBadge'

interface AgentCardProps {
  agent: Agent
  isSelected: boolean
  onSelect: (agent: Agent) => void
}

export default function AgentCard({ agent, isSelected, onSelect }: AgentCardProps) {
  const { theme } = useTheme()
  const statusColor = getStatusColor(theme, agent.status)

  return (
    <button
      onClick={() => onSelect(agent)}
      className="group flex w-full items-start gap-2.5 rounded-lg p-2.5 text-left transition-all duration-200"
      style={{
        backgroundColor: isSelected ? theme.global.border + '66' : 'transparent',
        outline: isSelected ? `1px solid ${theme.global.accent}80` : 'none',
      }}
    >
      <span className="mt-0.5 text-xl leading-none">{agent.icon}</span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium" style={{ color: theme.global.textPrimary }}>
            {agent.displayName}
          </span>
          <StatusBadge status={agent.status} showLabel={false} />
        </div>

        {agent.status === 'working' && agent.currentTask && (
          <div className="mt-1.5">
            <p className="truncate text-xs" style={{ color: theme.global.textSecondary }}>{agent.currentTask}</p>
            {agent.progress !== undefined && (
              <div className="mt-1 h-1 w-full overflow-hidden rounded-full" style={{ backgroundColor: theme.global.border }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${agent.progress}%`, backgroundColor: statusColor.dot }}
                />
              </div>
            )}
          </div>
        )}

        {agent.status === 'waiting' && agent.currentTask && (
          <p className="mt-1 truncate text-xs" style={{ color: theme.statuses.waiting.text + 'cc' }}>
            {agent.currentTask}
          </p>
        )}

        {agent.status === 'completed' && agent.currentTask && (
          <p className="mt-1 truncate text-xs" style={{ color: theme.statuses.completed.text + 'cc' }}>
            {agent.currentTask}
          </p>
        )}
      </div>
    </button>
  )
}
