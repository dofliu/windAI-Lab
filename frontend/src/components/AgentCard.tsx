import { Agent } from '../types/agent'
import StatusBadge from './StatusBadge'

interface AgentCardProps {
  agent: Agent
  isSelected: boolean
  onSelect: (agent: Agent) => void
}

export default function AgentCard({ agent, isSelected, onSelect }: AgentCardProps) {
  return (
    <button
      onClick={() => onSelect(agent)}
      className={`group flex w-full items-start gap-2.5 rounded-lg p-2.5 text-left transition-all duration-200
        ${
          isSelected
            ? 'bg-slate-600/40 ring-1 ring-indigo-500/50'
            : 'hover:bg-slate-700/40'
        }`}
    >
      <span className="mt-0.5 text-xl leading-none">{agent.icon}</span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-slate-100">
            {agent.displayName}
          </span>
          <StatusBadge status={agent.status} showLabel={false} />
        </div>

        {agent.status === 'working' && agent.currentTask && (
          <div className="mt-1.5">
            <p className="truncate text-xs text-slate-400">{agent.currentTask}</p>
            {agent.progress !== undefined && (
              <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-700">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${agent.progress}%` }}
                />
              </div>
            )}
          </div>
        )}

        {agent.status === 'waiting' && agent.currentTask && (
          <p className="mt-1 truncate text-xs text-amber-400/80">
            {agent.currentTask}
          </p>
        )}

        {agent.status === 'completed' && agent.currentTask && (
          <p className="mt-1 truncate text-xs text-blue-400/80">
            {agent.currentTask}
          </p>
        )}
      </div>
    </button>
  )
}
