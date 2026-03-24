import { useState, useEffect, useMemo, useRef } from 'react'
import { Agent, WorkLog, OfficeRoom, SpeechBubble } from '../types/agent'
import { initialAgents, initialRooms, initialWorkLogs } from '../utils/mockData'

/* ════════════════════════════════════════════
   Mission templates — 任務流程定義
   ════════════════════════════════════════════ */

interface Mission {
  name: string
  agentIds: string[]
  tasks: Record<string, string>
}

const MISSIONS: Mission[] = [
  {
    name: '風機故障診斷',
    agentIds: ['fault-diagnostician', 'scada-processor', 'predictive-modeler', 'quality-checker'],
    tasks: {
      'fault-diagnostician': '執行故障分類與嚴重度評估',
      'scada-processor': '匯入最新 SCADA 資料並預處理',
      'predictive-modeler': '預測剩餘使用壽命 (RUL)',
      'quality-checker': '驗證資料品質與完整性',
    },
  },
  {
    name: '風能預測論文撰寫',
    agentIds: ['paper-writer', 'literature-reviewer', 'research-lead'],
    tasks: {
      'paper-writer': '撰寫方法論章節',
      'literature-reviewer': '整理相關文獻比較表',
      'research-lead': '審閱實驗設計方案',
    },
  },
  {
    name: 'ML 模型訓練實驗',
    agentIds: ['model-trainer', 'experiment-tracker', 'hyperparameter-tuner', 'feature-engineer'],
    tasks: {
      'model-trainer': '訓練 XGBoost 功率預測模型',
      'experiment-tracker': '記錄實驗參數至 MLflow',
      'hyperparameter-tuner': '執行 Optuna 超參數搜索',
      'feature-engineer': '計算風速-功率特徵',
    },
  },
  {
    name: 'RAG 知識庫建置',
    agentIds: ['rag-architect', 'rag-curator', 'backend-dev'],
    tasks: {
      'rag-architect': '優化向量檢索管線',
      'rag-curator': '索引新批次論文文獻',
      'backend-dev': '實作 RAG API 端點',
    },
  },
  {
    name: '風場資料品質分析',
    agentIds: ['wind-resource-analyst', 'wake-analyst', 'power-curve-expert', 'data-validator'],
    tasks: {
      'wind-resource-analyst': '分析風場資源分佈',
      'wake-analyst': '模擬尾流效應影響',
      'power-curve-expert': '建立功率曲線模型',
      'data-validator': '驗證感測器資料範圍',
    },
  },
  {
    name: '前端儀表板開發',
    agentIds: ['frontend-dev', 'api-designer', 'devops-engineer'],
    tasks: {
      'frontend-dev': '實作即時監控圖表元件',
      'api-designer': '設計 WebSocket 訊息格式',
      'devops-engineer': '設定 CI/CD 自動部署流程',
    },
  },
]

const DIRECTOR_ID = 'project-director'

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function agentName(id: string): string {
  return initialAgents.find((a) => a.id === id)?.displayName ?? id
}

let logSeq = initialWorkLogs.length + 1

/* ════════════════════════════════════════════
   Simulation hook
   ════════════════════════════════════════════ */

export function useAgentSimulation() {
  const [agents, setAgents] = useState<Agent[]>(initialAgents)
  const [workLogs, setWorkLogs] = useState<WorkLog[]>(initialWorkLogs)
  const [bubbles, setBubbles] = useState<SpeechBubble[]>([])

  const agentsRef = useRef(agents)
  agentsRef.current = agents

  // Derive rooms from agents
  const rooms = useMemo<OfficeRoom[]>(
    () => initialRooms.map((room) => ({
      ...room,
      agents: agents.filter((a) => a.tier === room.tier),
    })),
    [agents],
  )

  /* ── Helpers ── */

  const addLog = (aId: string, message: string, type: WorkLog['type'] = 'info') => {
    setWorkLogs((prev) => {
      const next = [...prev, {
        id: `log-${logSeq++}`,
        timestamp: new Date(),
        agentId: aId,
        agentName: agentName(aId),
        message,
        type,
      }]
      return next.length > 100 ? next.slice(-100) : next
    })
  }

  const batchUpdate = (updates: Record<string, Partial<Agent>>) => {
    setAgents((prev) => prev.map((a) => {
      const u = updates[a.id]
      return u ? { ...a, ...u } : a
    }))
  }

  const showBubble = (aId: string, text: string) => {
    setBubbles([{ id: `b-${Date.now()}`, agentId: aId, text, timestamp: new Date() }])
  }

  const clearBubbles = () => setBubbles([])

  /* ── Mission lifecycle ── */

  useEffect(() => {
    let cancelled = false
    const timers: ReturnType<typeof setTimeout>[] = []
    let progressInterval: ReturnType<typeof setInterval> | null = null

    function sched(fn: () => void, ms: number) {
      if (cancelled) return
      const t = setTimeout(() => { if (!cancelled) fn() }, ms)
      timers.push(t)
    }

    function runMission() {
      if (cancelled) return
      const mission = randomItem(MISSIONS)
      const names = mission.agentIds.map(agentName).join('、')

      // ═══ Phase 1: Director announces (0s) ═══
      const announcement = `收到任務！請${names}到會議室集合。`
      showBubble(DIRECTOR_ID, announcement)
      batchUpdate({
        [DIRECTOR_ID]: { status: 'working', currentTask: `指派任務：${mission.name}`, progress: undefined },
      })
      addLog(DIRECTOR_ID, announcement)

      // ═══ Phase 2: Agents gather (3.5s) ═══
      sched(() => {
        clearBubbles()
        const updates: Record<string, Partial<Agent>> = {
          [DIRECTOR_ID]: { status: 'waiting', currentTask: '前往會議室主持...' },
        }
        mission.agentIds.forEach((id) => {
          updates[id] = { status: 'waiting', currentTask: '前往會議室...', progress: undefined }
        })
        batchUpdate(updates)
        addLog(DIRECTOR_ID, `召集${names}前往會議室`)
      }, 3500)

      // ═══ Phase 3: Assign & start working (6.5s) ═══
      sched(() => {
        showBubble(DIRECTOR_ID, `${mission.name}：開始分配工作！`)
        addLog(DIRECTOR_ID, `開始分配 ${mission.name} 任務`)

        sched(() => clearBubbles(), 2500)

        const updates: Record<string, Partial<Agent>> = {
          [DIRECTOR_ID]: { status: 'working', currentTask: `監督：${mission.name}`, progress: undefined },
        }
        mission.agentIds.forEach((id) => {
          const task = mission.tasks[id] ?? '處理中...'
          updates[id] = {
            status: 'working',
            currentTask: task,
            progress: 5,
            collaboratingWith: mission.agentIds.filter((x) => x !== id),
          }
          addLog(id, `開始：${task}`)
        })
        batchUpdate(updates)

        // ═══ Phase 3b: Progress ticking ═══
        progressInterval = setInterval(() => {
          if (cancelled) {
            if (progressInterval) clearInterval(progressInterval)
            return
          }

          setAgents((prev) => prev.map((a) => {
            if (!mission.agentIds.includes(a.id) || a.status !== 'working' || a.progress === undefined) return a
            const inc = Math.random() * 14 + 4
            return { ...a, progress: Math.min(100, Math.round(a.progress + inc)) }
          }))

          // Check if all done (read from ref after a tick)
          sched(() => {
            const cur = agentsRef.current
            const allDone = mission.agentIds.every((id) => {
              const a = cur.find((x) => x.id === id)
              return a && (a.progress ?? 0) >= 100
            })
            if (!allDone || !progressInterval) return

            clearInterval(progressInterval)
            progressInterval = null

            // ═══ Phase 4: Complete & return ═══
            sched(() => {
              showBubble(DIRECTOR_ID, `${mission.name} 全部完成，辛苦了！大家回座位吧。`)
              const updates: Record<string, Partial<Agent>> = {
                [DIRECTOR_ID]: { status: 'completed', currentTask: `${mission.name} 已完成` },
              }
              mission.agentIds.forEach((id) => {
                const task = mission.tasks[id] ?? '任務'
                updates[id] = { status: 'completed', currentTask: `已完成：${task}`, progress: 100 }
                addLog(id, `完成：${task}`, 'success')
              })
              addLog(DIRECTOR_ID, `${mission.name} 所有任務已完成`, 'success')
              batchUpdate(updates)

              // ═══ Phase 5: Walk back to desks (3s) ═══
              sched(() => {
                clearBubbles()
                const updates: Record<string, Partial<Agent>> = {
                  [DIRECTOR_ID]: { status: 'idle', currentTask: undefined, progress: undefined },
                }
                mission.agentIds.forEach((id) => {
                  updates[id] = { status: 'idle', currentTask: undefined, progress: undefined, collaboratingWith: undefined }
                })
                batchUpdate(updates)

                // ═══ Schedule next mission ═══
                sched(runMission, 5000 + Math.random() * 8000)
              }, 3500) // walk back
            }, 500) // brief pause
          }, 80) // let state settle
        }, 1500) // progress tick interval
      }, 6500) // announce + gather duration
    }

    // Start first mission after 2s
    sched(runMission, 2000)

    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
      if (progressInterval) clearInterval(progressInterval)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { agents, rooms, workLogs, speechBubbles: bubbles }
}
