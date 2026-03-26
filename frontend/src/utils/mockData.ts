import { Agent, WorkLog, OfficeRoom } from '../types/agent'

/**
 * 核心代理清單 — 對應 configs/agents/registry/ 中 core: true 的 12 個代理。
 * 模擬模式使用此清單作為初始狀態。
 * 後端連線後由 WebSocket initial_state 覆蓋。
 */
export const initialAgents: Agent[] = [
  // ── Tier 1: Leadership (wLab:) — 2 core ──
  {
    id: 'project-director',
    name: 'wLab:project-director',
    displayName: '專案總監',
    tier: 'leadership',
    status: 'idle',
    color: '#f59e0b',
    icon: '👔',
  },
  {
    id: 'project-manager',
    name: 'wLab:project-manager',
    displayName: '專案經理',
    tier: 'leadership',
    status: 'idle',
    color: '#f59e0b',
    icon: '📋',
  },
  // ── Tier 2: Data (wData:) — 2 core ──
  {
    id: 'scada-processor',
    name: 'wData:scada-processor',
    displayName: 'SCADA 資料工程師',
    tier: 'data',
    status: 'idle',
    color: '#10b981',
    icon: '📡',
  },
  {
    id: 'quality-checker',
    name: 'wData:quality-checker',
    displayName: '品質檢查師',
    tier: 'data',
    status: 'idle',
    color: '#10b981',
    icon: '✅',
  },
  // ── Tier 3: AI/ML (wAI:) — 5 core ──
  {
    id: 'fault-diagnostician',
    name: 'wAI:fault-diagnostician',
    displayName: '故障診斷師',
    tier: 'ai-ml',
    status: 'idle',
    color: '#8b5cf6',
    icon: '🔧',
  },
  {
    id: 'predictive-modeler',
    name: 'wAI:predictive-modeler',
    displayName: '預測模型師',
    tier: 'ai-ml',
    status: 'idle',
    color: '#8b5cf6',
    icon: '📈',
  },
  {
    id: 'anomaly-detector',
    name: 'wAI:anomaly-detector',
    displayName: '異常偵測師',
    tier: 'ai-ml',
    status: 'idle',
    color: '#8b5cf6',
    icon: '🔍',
  },
  {
    id: 'feature-engineer',
    name: 'wAI:feature-engineer',
    displayName: '特徵工程師',
    tier: 'ai-ml',
    status: 'idle',
    color: '#8b5cf6',
    icon: '⚙️',
  },
  {
    id: 'rag-architect',
    name: 'wAI:rag-architect',
    displayName: 'RAG 架構師',
    tier: 'ai-ml',
    status: 'idle',
    color: '#8b5cf6',
    icon: '🧠',
  },
  // ── Tier 4: Domain (wDomain:) — 2 core ──
  {
    id: 'power-curve-expert',
    name: 'wDomain:power-curve-expert',
    displayName: '功率曲線專家',
    tier: 'domain',
    status: 'idle',
    color: '#ec4899',
    icon: '📊',
  },
  {
    id: 'maintenance-planner',
    name: 'wDomain:maintenance-planner',
    displayName: '維護規劃師',
    tier: 'domain',
    status: 'idle',
    color: '#ec4899',
    icon: '🔩',
  },
  // ── Tier 6: Research (wRes:) — 1 core ──
  {
    id: 'paper-writer',
    name: 'wRes:paper-writer',
    displayName: '論文撰寫員',
    tier: 'research',
    status: 'idle',
    color: '#06b6d4',
    icon: '✏️',
  },
]

// ── Tier 顏色定義 ──

export const tierColors: Record<string, { bg: string; border: string; text: string; badge: string; accent: string }> = {
  leadership:  { bg: 'bg-amber-950/30',   border: 'border-amber-700/40',   text: 'text-amber-400',   badge: 'bg-amber-500/20 text-amber-300',   accent: '#f59e0b' },
  data:        { bg: 'bg-emerald-950/30',  border: 'border-emerald-700/40', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-300', accent: '#10b981' },
  'ai-ml':     { bg: 'bg-violet-950/30',   border: 'border-violet-700/40',  text: 'text-violet-400',  badge: 'bg-violet-500/20 text-violet-300',  accent: '#8b5cf6' },
  domain:      { bg: 'bg-rose-950/30',     border: 'border-rose-700/40',    text: 'text-rose-400',    badge: 'bg-rose-500/20 text-rose-300',      accent: '#ec4899' },
  engineering: { bg: 'bg-orange-950/30',   border: 'border-orange-700/40',  text: 'text-orange-400',  badge: 'bg-orange-500/20 text-orange-300',  accent: '#f97316' },
  research:    { bg: 'bg-cyan-950/30',     border: 'border-cyan-700/40',    text: 'text-cyan-400',    badge: 'bg-cyan-500/20 text-cyan-300',      accent: '#06b6d4' },
}

// ── 辦公室房間定義 ──

export const initialRooms: OfficeRoom[] = [
  {
    id: 'leadership',
    name: '指揮中心',
    tier: 'leadership',
    agents: initialAgents.filter((a) => a.tier === 'leadership'),
    icon: '🏛️',
    position: { row: 0, col: 0 },
  },
  {
    id: 'data',
    name: '資料工程室',
    tier: 'data',
    agents: initialAgents.filter((a) => a.tier === 'data'),
    icon: '🗃️',
    position: { row: 0, col: 1 },
  },
  {
    id: 'ai-ml',
    name: '模型實驗室',
    tier: 'ai-ml',
    agents: initialAgents.filter((a) => a.tier === 'ai-ml'),
    icon: '🧠',
    position: { row: 0, col: 2 },
  },
  {
    id: 'domain',
    name: '領域知識庫',
    tier: 'domain',
    agents: initialAgents.filter((a) => a.tier === 'domain'),
    icon: '🌬️',
    position: { row: 1, col: 0 },
  },
  {
    id: 'engineering',
    name: '軟體工程室',
    tier: 'engineering',
    agents: initialAgents.filter((a) => a.tier === 'engineering'),
    icon: '💻',
    position: { row: 1, col: 1 },
  },
  {
    id: 'research',
    name: '研究室',
    tier: 'research',
    agents: initialAgents.filter((a) => a.tier === 'research'),
    icon: '📖',
    position: { row: 1, col: 2 },
  },
]

// ── 模擬用初始日誌 ──

export const initialWorkLogs: WorkLog[] = [
  {
    id: 'log-0',
    timestamp: new Date(),
    agentId: 'system',
    agentName: 'WindAI Lab',
    message: '系統已啟動，12 位核心代理就緒',
    type: 'info',
  },
]

// ── 模擬用隨機任務 ──

export const simulationTasks: Record<string, string[]> = {
  'project-director': [
    '審核本週研究進度報告',
    '協調跨團隊任務分配',
    '召開專案進度會議',
  ],
  'scada-processor': [
    '匯入新批次 SCADA 原始資料',
    '執行 10 分鐘均值重採樣',
    '轉換時區至 UTC 標準',
  ],
  'fault-diagnostician': [
    '分析風機葉片振動異常訊號',
    '建立故障預測分類模型',
    '生成設備健康狀態報告',
  ],
  'predictive-modeler': [
    '訓練風速時序預測模型',
    '比較不同模型的 MAE 與 RMSE',
    '執行 RUL 退化趨勢分析',
  ],
  'power-curve-expert': [
    '訓練 NBM 功率曲線模型',
    '分析功率偏差趨勢',
    '產出功率曲線偏差報告',
  ],
  'quality-checker': [
    '執行資料品質報告生成',
    '驗證感測器量測範圍',
    '統計各欄位缺失率',
  ],
  'paper-writer': [
    '撰寫方法論章節初稿',
    '整理實驗結果圖表',
    '校對論文格式',
  ],
}

export const simulationLogMessages: Record<string, string[]> = {
  'project-director': [
    '已收到本週進度報告，正在審核各團隊成果',
    '已完成任務分配，通知相關成員',
  ],
  'scada-processor': [
    '已匯入 Kelmarsh 風場 SCADA 資料',
    '10 分鐘均值重採樣完成',
  ],
  'fault-diagnostician': [
    '故障分類模型準確率達 94.7%',
    'SCADA 數據匯入完成',
  ],
  'predictive-modeler': [
    '模型評估完成：MAE=2.31, RMSE=3.15',
    'RUL 退化趨勢分析完成',
  ],
  'quality-checker': [
    '資料品質報告已生成：整體完整度 97.2%',
    '已標記可疑資料點',
  ],
  'paper-writer': [
    '方法論段落初稿完成',
    '論文格式檢查通過',
  ],
}
