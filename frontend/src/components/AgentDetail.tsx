import { Agent, WorkLog } from '../types/agent'
import StatusBadge from './StatusBadge'

interface AgentDetailProps {
  agent: Agent | null
  allAgents: Agent[]
  workLogs: WorkLog[]
}

export default function AgentDetail({
  agent,
  allAgents,
  workLogs,
}: AgentDetailProps) {
  if (!agent) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4 text-center text-slate-500">
        <span className="mb-3 text-4xl">👈</span>
        <p className="text-sm">選擇一位研究員以檢視詳細資訊</p>
      </div>
    )
  }

  const agentLogs = workLogs
    .filter((log) => log.agentId === agent.id)
    .slice(-8)

  const collaborators = (agent.collaboratingWith ?? [])
    .map((id) => allAgents.find((a) => a.id === id))
    .filter(Boolean) as Agent[]

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Header */}
      <div className="border-b border-slate-700/50 p-4">
        <div className="mb-3 flex items-center gap-3">
          <span className="text-4xl">{agent.icon}</span>
          <div>
            <h2 className="text-lg font-bold text-slate-100">
              {agent.displayName}
            </h2>
            <p className="text-xs text-slate-500">{agent.name}</p>
          </div>
        </div>
        <StatusBadge status={agent.status} size="md" />
      </div>

      {/* Task & Progress */}
      {agent.currentTask && (
        <div className="border-b border-slate-700/50 p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            目前任務
          </h3>
          <p className="text-sm text-slate-200">{agent.currentTask}</p>
          {agent.progress !== undefined && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-xs text-slate-400">
                <span>進度</span>
                <span>{agent.progress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-700">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                  style={{ width: `${agent.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Collaborators */}
      {collaborators.length > 0 && (
        <div className="border-b border-slate-700/50 p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            協作成員
          </h3>
          <div className="flex flex-wrap gap-2">
            {collaborators.map((c) => (
              <span
                key={c.id}
                className="inline-flex items-center gap-1.5 rounded-full bg-slate-700/60 px-3 py-1 text-xs text-slate-300"
              >
                <span>{c.icon}</span>
                {c.displayName}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="flex-1 p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          近期活動
        </h3>
        {agentLogs.length === 0 ? (
          <p className="text-xs text-slate-600">尚無活動紀錄</p>
        ) : (
          <div className="space-y-2">
            {agentLogs.map((log) => (
              <div key={log.id} className="text-xs">
                <span className="text-slate-500">
                  {log.timestamp.toLocaleTimeString('zh-TW', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                <p className="mt-0.5 text-slate-300">{log.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
