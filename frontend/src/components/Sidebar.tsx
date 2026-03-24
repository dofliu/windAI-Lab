import { useState } from 'react'
import { Agent, WorkLog } from '../types/agent'
import AgentDetail from './AgentDetail'
import WorkLogPanel from './WorkLogPanel'

interface SidebarProps {
  agent: Agent | null
  allAgents: Agent[]
  workLogs: WorkLog[]
}

type Tab = 'detail' | 'logs'

export default function Sidebar({ agent, allAgents, workLogs }: SidebarProps) {
  const [tab, setTab] = useState<Tab>('detail')

  // Auto-switch to detail when an agent is selected
  const activeTab = agent ? tab : 'logs'

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-slate-700/50">
        <button
          onClick={() => setTab('detail')}
          className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
            activeTab === 'detail'
              ? 'border-b-2 border-indigo-500 text-indigo-400'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          代理詳情
        </button>
        <button
          onClick={() => setTab('logs')}
          className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
            activeTab === 'logs'
              ? 'border-b-2 border-indigo-500 text-indigo-400'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          工作日誌
          <span className="ml-1 rounded-full bg-slate-700/60 px-1.5 py-0.5 text-[9px] text-slate-400">
            {workLogs.length}
          </span>
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'detail' ? (
          <AgentDetail agent={agent} allAgents={allAgents} workLogs={workLogs} />
        ) : (
          <WorkLogPanel logs={workLogs} />
        )}
      </div>
    </div>
  )
}
