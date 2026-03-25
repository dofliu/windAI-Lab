import { useState } from 'react'
import { Agent, WorkLog } from '../types/agent'
import AgentDetail from './AgentDetail'
import KnowledgeBasePanel from './KnowledgeBasePanel'
import MLDashboard from './MLDashboard'
import ScadaDashboard from './ScadaDashboard'
import WorkLogPanel from './WorkLogPanel'

interface SidebarProps {
  agent: Agent | null
  allAgents: Agent[]
  workLogs: WorkLog[]
}

type Tab = 'detail' | 'logs' | 'ml' | 'scada' | 'kb'

export default function Sidebar({ agent, allAgents, workLogs }: SidebarProps) {
  const [tab, setTab] = useState<Tab>('detail')

  // Auto-switch to detail when an agent is selected
  const activeTab = agent ? tab : tab === 'detail' ? 'logs' : tab

  const tabs: { id: Tab; label: string; color: string }[] = [
    { id: 'detail', label: '詳情', color: 'indigo' },
    { id: 'logs', label: '日誌', color: 'indigo' },
    { id: 'ml', label: 'ML', color: 'emerald' },
    { id: 'scada', label: 'SCADA', color: 'cyan' },
    { id: 'kb', label: '知識庫', color: 'violet' },
  ]

  const colorMap: Record<string, string> = {
    indigo: 'border-indigo-500 text-indigo-400',
    emerald: 'border-emerald-500 text-emerald-400',
    cyan: 'border-cyan-500 text-cyan-400',
    violet: 'border-violet-500 text-violet-400',
  }

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-slate-700/50">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 px-1 py-2 text-[9px] font-medium transition-colors ${
              activeTab === t.id
                ? `border-b-2 ${colorMap[t.color]}`
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t.label}
            {t.id === 'logs' && (
              <span className="ml-0.5 rounded-full bg-slate-700/60 px-1 py-0.5 text-[8px] text-slate-400">
                {workLogs.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'detail' ? (
          <AgentDetail agent={agent} allAgents={allAgents} workLogs={workLogs} />
        ) : activeTab === 'ml' ? (
          <MLDashboard />
        ) : activeTab === 'scada' ? (
          <ScadaDashboard />
        ) : activeTab === 'kb' ? (
          <KnowledgeBasePanel />
        ) : (
          <WorkLogPanel logs={workLogs} />
        )}
      </div>
    </div>
  )
}
