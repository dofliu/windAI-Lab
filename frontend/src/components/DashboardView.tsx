import { useState, useEffect } from 'react'
import { Agent, WorkLog } from '../types/agent'
import AgentDetail from './AgentDetail'
import AgentManagement from './AgentManagement'
import FileWatcherStatus from './FileWatcherStatus'
import KnowledgeBasePanel from './KnowledgeBasePanel'
import MLDashboard from './MLDashboard'
import ScadaDashboard from './ScadaDashboard'
import WorkflowDAG from './WorkflowDAG'
import WorkLogPanel from './WorkLogPanel'

type DashTab = 'detail' | 'scada' | 'ml' | 'kb' | 'dag' | 'hr' | 'logs'

interface FileEventPayload {
  filename: string
  path: string
  turbine_id: string | null
  size_display: string
  total_records: number
  detected_fields: Record<string, string> | null
  analysis_summary: {
    numeric_columns: number
    target_column: string | null
    top_features: string[]
    anomaly_columns: number
  } | null
  error_message: string | null
}

interface DashboardViewProps {
  workLogs: WorkLog[]
  selectedAgent?: Agent | null
  allAgents?: Agent[]
  fileEvents?: FileEventPayload[]
  onHireAgent?: (agent: { id: string; name: string; display_name: string; tier: string; color: string; icon: string }) => void
  onFireAgent?: (agentId: string) => void
}

const TABS: { id: DashTab; label: string; icon: string; color: string }[] = [
  { id: 'detail', label: '詳情', icon: '👤', color: 'indigo' },
  { id: 'scada',  label: 'SCADA 資料', icon: '📊', color: 'cyan' },
  { id: 'ml',     label: 'ML Pipeline', icon: '🧠', color: 'emerald' },
  { id: 'kb',     label: '知識庫',      icon: '📚', color: 'violet' },
  { id: 'dag',    label: '流程圖',      icon: '🔀', color: 'orange' },
  { id: 'hr',     label: '人事管理',    icon: '👥', color: 'amber' },
  { id: 'logs',   label: '工作日誌',    icon: '📝', color: 'slate' },
]

const ACTIVE_COLORS: Record<string, string> = {
  indigo:  'border-indigo-500 text-indigo-400 bg-indigo-500/10',
  cyan:    'border-cyan-500 text-cyan-400 bg-cyan-500/10',
  emerald: 'border-emerald-500 text-emerald-400 bg-emerald-500/10',
  violet:  'border-violet-500 text-violet-400 bg-violet-500/10',
  orange:  'border-orange-500 text-orange-400 bg-orange-500/10',
  amber:   'border-amber-500 text-amber-400 bg-amber-500/10',
  slate:   'border-slate-500 text-slate-300 bg-slate-500/10',
}

export default function DashboardView({ workLogs, selectedAgent, allAgents = [], fileEvents = [], onHireAgent, onFireAgent }: DashboardViewProps) {
  const [activeTab, setActiveTab] = useState<DashTab>('scada')

  // Auto-switch to detail tab when an agent is selected
  useEffect(() => {
    if (selectedAgent) setActiveTab('detail')
  }, [selectedAgent?.id])

  return (
    <div className="flex h-full flex-col">
      {/* File Watcher Status */}
      <div className="shrink-0 px-4 pt-2">
        <FileWatcherStatus fileEvents={fileEvents} />
      </div>

      {/* Tab bar */}
      <div className="flex shrink-0 items-center gap-1 border-b border-slate-700/50 bg-slate-800/60 px-4 py-1.5">
        {TABS.map((tab) => {
          // Show dot on detail tab when agent is selected
          const hasAgent = tab.id === 'detail' && selectedAgent
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                activeTab === tab.id
                  ? `border ${ACTIVE_COLORS[tab.color]}`
                  : 'border border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-700/30'
              }`}
            >
              <span className="text-sm">{tab.icon}</span>
              {tab.label}
              {hasAgent && activeTab !== 'detail' && (
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
              )}
              {tab.id === 'dag' && allAgents.filter((a) => a.status === 'working').length > 0 && (
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              )}
              {tab.id === 'logs' && (
                <span className="ml-1 rounded-full bg-slate-700 px-1.5 py-0.5 text-[9px] text-slate-400">
                  {workLogs.length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Content area — full width */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'detail' ? (
          <AgentDetail agent={selectedAgent ?? null} allAgents={allAgents} workLogs={workLogs} />
        ) : activeTab === 'scada' ? (
          <ScadaDashboard />
        ) : activeTab === 'ml' ? (
          <MLDashboard />
        ) : activeTab === 'kb' ? (
          <KnowledgeBasePanel />
        ) : activeTab === 'dag' ? (
          <WorkflowDAG agents={allAgents} title="代理協作流程" />
        ) : activeTab === 'hr' ? (
          <AgentManagement allAgents={allAgents} onHire={onHireAgent} onFire={onFireAgent} />
        ) : (
          <WorkLogPanel logs={workLogs} />
        )}
      </div>
    </div>
  )
}
