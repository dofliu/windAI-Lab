import { useState, useEffect } from 'react'
import { Agent, WorkLog, TaskRecord, Alert, WorkOrder } from '../types/agent'
import { useTheme } from '../themes'
import AgentDetail from './AgentDetail'
import AgentManagement from './AgentManagement'
import AlertPanel from './AlertPanel'
import KnowledgeBasePanel from './KnowledgeBasePanel'
import MLDashboard from './MLDashboard'
import ScadaDashboard from './ScadaDashboard'
import TaskHistoryList from './TaskHistoryList'
import WorkflowDAG from './WorkflowDAG'
import WorkLogPanel from './WorkLogPanel'
import WorkOrderPanel from './WorkOrderPanel'

export type DashTab = 'team' | 'analysis' | 'knowledge' | 'records' | 'alerts'
type SubView = 'detail' | 'hr' | 'scada' | 'ml' | 'dag' | 'kb' | 'logs' | 'history' | 'alert-list' | 'work-orders'

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
  taskHistory?: TaskRecord[]
  onDeleteTaskRecord?: (id: string) => void
  onClearTaskHistory?: () => void
  initialTab?: DashTab
  onTabChange?: (tab: DashTab) => void
  alerts?: Alert[]
  onAlertsChange?: (alerts: Alert[]) => void
  workOrders?: WorkOrder[]
}

const TABS: { id: DashTab; label: string; icon: string; subViews: { id: SubView; label: string }[] }[] = [
  {
    id: 'team',
    label: '團隊',
    icon: '👥',
    subViews: [
      { id: 'detail', label: '代理詳情' },
      { id: 'hr', label: '人事管理' },
    ],
  },
  {
    id: 'analysis',
    label: '分析',
    icon: '📊',
    subViews: [
      { id: 'scada', label: 'SCADA 資料' },
      { id: 'ml', label: 'ML Pipeline' },
      { id: 'dag', label: '流程圖' },
    ],
  },
  {
    id: 'knowledge',
    label: '知識',
    icon: '📚',
    subViews: [
      { id: 'kb', label: '知識庫' },
    ],
  },
  {
    id: 'records',
    label: '紀錄',
    icon: '🗂️',
    subViews: [
      { id: 'logs', label: '工作日誌' },
      { id: 'history', label: '歷史記錄' },
    ],
  },
  {
    id: 'alerts',
    label: '警報',
    icon: '🚨',
    subViews: [
      { id: 'alert-list', label: '警報列表' },
      { id: 'work-orders', label: '工單管理' },
    ],
  },
]

export default function DashboardView({
  workLogs, selectedAgent, allAgents = [], fileEvents: _fileEvents = [],
  onHireAgent, onFireAgent,
  taskHistory, onDeleteTaskRecord, onClearTaskHistory,
  initialTab, onTabChange,
  alerts = [], onAlertsChange, workOrders = [],
}: DashboardViewProps) {
  const { theme } = useTheme()
  const [activeTab, setActiveTab] = useState<DashTab>('analysis')
  const [activeSubView, setActiveSubView] = useState<SubView>('scada')

  // Auto-switch when agent selected
  useEffect(() => {
    if (selectedAgent) {
      setActiveTab('team')
      setActiveSubView('detail')
    }
  }, [selectedAgent?.id])

  // External navigation
  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab)
      const tab = TABS.find((t) => t.id === initialTab)
      if (tab) setActiveSubView(tab.subViews[0].id)
      onTabChange?.(initialTab)
    }
  }, [initialTab])

  const currentTab = TABS.find((t) => t.id === activeTab)!

  const handleTabChange = (tabId: DashTab) => {
    setActiveTab(tabId)
    const tab = TABS.find((t) => t.id === tabId)!
    setActiveSubView(tab.subViews[0].id)
  }

  return (
    <div className="flex h-full flex-col">
      {/* ── Tab bar ── */}
      <div
        className="flex shrink-0 items-center border-b px-4 py-1"
        style={{ borderColor: theme.global.border, backgroundColor: theme.global.headerBg + '80' }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all rounded-md mr-1"
              style={{
                backgroundColor: isActive ? theme.global.accent + '15' : 'transparent',
                color: isActive ? theme.global.accent : theme.global.textMuted,
                borderBottom: isActive ? `2px solid ${theme.global.accent}` : '2px solid transparent',
              }}
            >
              <span className="text-sm">{tab.icon}</span>
              {tab.label}
              {tab.id === 'team' && selectedAgent && !isActive && (
                <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ backgroundColor: theme.global.accent }} />
              )}
              {tab.id === 'alerts' && alerts.filter(a => a.status === 'active').length > 0 && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[9px]"
                  style={{
                    backgroundColor: alerts.some(a => a.severity === 'critical' && a.status === 'active') ? '#ef444430' : '#f59e0b30',
                    color: alerts.some(a => a.severity === 'critical' && a.status === 'active') ? '#ef4444' : '#f59e0b',
                  }}
                >
                  {alerts.filter(a => a.status === 'active').length}
                </span>
              )}
              {tab.id === 'records' && (taskHistory?.length ?? 0) > 0 && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[9px]"
                  style={{ backgroundColor: theme.global.border, color: theme.global.textSecondary }}
                >
                  {taskHistory!.length}
                </span>
              )}
            </button>
          )
        })}

        {/* Sub-view pills (如果有多個) */}
        {currentTab.subViews.length > 1 && (
          <>
            <div className="mx-2 h-4 w-px" style={{ backgroundColor: theme.global.border }} />
            {currentTab.subViews.map((sv) => (
              <button
                key={sv.id}
                onClick={() => setActiveSubView(sv.id)}
                className="px-2 py-1 text-[10px] rounded transition-colors mr-0.5"
                style={{
                  backgroundColor: activeSubView === sv.id ? theme.global.border + '60' : 'transparent',
                  color: activeSubView === sv.id ? theme.global.textPrimary : theme.global.textMuted,
                }}
              >
                {sv.label}
              </button>
            ))}
          </>
        )}
      </div>

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeSubView === 'detail' ? (
          <AgentDetail agent={selectedAgent ?? null} allAgents={allAgents} workLogs={workLogs} />
        ) : activeSubView === 'hr' ? (
          <AgentManagement allAgents={allAgents} onHire={onHireAgent} onFire={onFireAgent} />
        ) : activeSubView === 'scada' ? (
          <ScadaDashboard />
        ) : activeSubView === 'ml' ? (
          <MLDashboard />
        ) : activeSubView === 'dag' ? (
          <WorkflowDAG agents={allAgents} title="代理協作流程" />
        ) : activeSubView === 'kb' ? (
          <KnowledgeBasePanel />
        ) : activeSubView === 'history' ? (
          <TaskHistoryList
            records={taskHistory ?? []}
            onDeleteRecord={onDeleteTaskRecord ?? (() => {})}
            onClearAll={onClearTaskHistory ?? (() => {})}
          />
        ) : activeSubView === 'alert-list' ? (
          <AlertPanel alerts={alerts} onAlertsChange={onAlertsChange} />
        ) : activeSubView === 'work-orders' ? (
          <WorkOrderPanel workOrders={workOrders} allAgents={allAgents} />
        ) : (
          <WorkLogPanel logs={workLogs} />
        )}
      </div>
    </div>
  )
}
