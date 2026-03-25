import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { Agent, WorkLog, OfficeRoom, SpeechBubble } from '../types/agent'
import { initialAgents, initialRooms, initialWorkLogs } from '../utils/mockData'

/* ════════════════════════════════════════════
   Mission templates — 任務流程定義
   ════════════════════════════════════════════ */

interface Mission {
  name: string
  agentIds: string[]
  tasks: Record<string, string>
  /** 每個代理在各進度階段的氣泡文字（簡短 ≤4 字） */
  progressLabels: Record<string, string[]>
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
    progressLabels: {
      'fault-diagnostician': ['載入資料', '特徵萃取', '故障分類', '嚴重度評估'],
      'scada-processor': ['讀取檔案', '解析欄位', '資料清洗', '格式轉換'],
      'predictive-modeler': ['健康指標', '退化擬合', 'RUL 計算', '信賴區間'],
      'quality-checker': ['完整度檢查', '範圍驗證', '品質標記', '報告彙整'],
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
    progressLabels: {
      'paper-writer': ['擬定大綱', '撰寫初稿', '修訂措辭', '排版校對'],
      'literature-reviewer': ['文獻搜索', '篩選分類', '比較整理', '引用彙整'],
      'research-lead': ['閱讀草稿', '方法審查', '結果驗證', '綜合評語'],
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
    progressLabels: {
      'model-trainer': ['載入資料', '模型訓練', '交叉驗證', '儲存模型'],
      'experiment-tracker': ['初始化 run', '記錄參數', '記錄指標', '產出報告'],
      'hyperparameter-tuner': ['定義空間', '搜索中...', '最佳組合', '回報結果'],
      'feature-engineer': ['原始特徵', '衍生計算', '重要度排序', '輸出完成'],
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
    progressLabels: {
      'rag-architect': ['分析查詢', '優化索引', '測試召回', '效能調校'],
      'rag-curator': ['解析文件', '切割分段', '向量嵌入', '索引建置'],
      'backend-dev': ['API 設計', '端點實作', '錯誤處理', '整合測試'],
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
    progressLabels: {
      'wind-resource-analyst': ['風速統計', 'Weibull 擬合', '風花圖', '發電預估'],
      'wake-analyst': ['風場建模', '尾流模擬', '效應計算', '結果匯出'],
      'power-curve-expert': ['資料篩選', 'NBM 訓練', '偏差分析', '報告產出'],
      'data-validator': ['範圍檢查', '一致性驗證', '品質標記', '結果彙整'],
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
    progressLabels: {
      'frontend-dev': ['元件設計', '實作邏輯', '樣式調整', '效能優化'],
      'api-designer': ['格式定義', '文件撰寫', '範例測試', '版本確認'],
      'devops-engineer': ['腳本撰寫', '流程設定', '部署測試', '監控確認'],
    },
  },
]

const DIRECTOR_ID = 'project-director'

/** 泡泡自動消失時間 (ms) */
const BUBBLE_TTL = 4000

// Reset all initial agents to idle so first mission speech bubble is clearly visible
const idleAgents: Agent[] = initialAgents.map((a) => ({
  ...a,
  status: 'idle' as const,
  currentTask: undefined,
  progress: undefined,
  collaboratingWith: undefined,
}))

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function pickRandom<T>(arr: T[], n: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(n, arr.length))
}

function agentName(id: string): string {
  return initialAgents.find((a) => a.id === id)?.displayName ?? id
}

let logSeq = initialWorkLogs.length + 1

/* ════════════════════════════════════════════
   氣泡策略 1: 任務進行中 — 閒置員工微反應
   只有 2~3 個隨機閒置員工，顯示 emoji 或 ≤2 字
   ════════════════════════════════════════════ */

const IDLE_MICRO_REACTIONS: string[] = [
  '👀', '🤔', '💪', '👍', '☕', '📝', '😊', '💻',
  '🔍', '📊', '⚡', '✅', '🎯', '📈', '🧠', '🌬️',
  '嗯', '好的', '收到', '加油', '不錯', '哈',
  '噢', 'OK', '嘿', '讚', '喔', '嗯嗯',
]

/* ════════════════════════════════════════════
   氣泡策略 2: 全場閒置 10 分鐘 — 辦公室日常對話
   隨機 5 個員工，氣泡文字 ≤5 字
   ════════════════════════════════════════════ */

const IDLE_OFFICE_CHAT: string[] = [
  '好無聊...', '☕ 喝咖啡', '午餐吃啥？', '快下班了', '天氣好好',
  '要開會嗎', '好想睡 😴', '週五了！', '加油加油', '看個新聞',
  '休息一下', '伸展筋骨', '出去走走', '好累喔', '寫文件中',
  '來杯茶 🍵', '整理桌面', '回個信', '查個資料', '等消息中',
  '打個哈欠', '看報告...', '還好嗎？', '嗯嗯', '好的 👌',
  '☀️ 好熱', '下雨了 🌧️', '肚子餓了', '😎', '💤',
]

/* ════════════════════════════════════════════
   Simulation hook
   ════════════════════════════════════════════ */

export function useAgentSimulation() {
  const [agents, setAgents] = useState<Agent[]>(idleAgents)
  const [workLogs, setWorkLogs] = useState<WorkLog[]>(initialWorkLogs)
  const [bubbles, setBubbles] = useState<SpeechBubble[]>([])

  const agentsRef = useRef(agents)
  agentsRef.current = agents

  /** 上次有任務的時間戳 */
  const lastMissionEndRef = useRef<number>(0)
  /** 是否有任務進行中 */
  const missionActiveRef = useRef(false)

  // Derive rooms from agents
  const rooms = useMemo<OfficeRoom[]>(
    () => initialRooms.map((room) => ({
      ...room,
      agents: agents.filter((a) => a.tier === room.tier),
    })),
    [agents],
  )

  /* ── Helpers ── */

  const addLog = useCallback((aId: string, message: string, type: WorkLog['type'] = 'info') => {
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
  }, [])

  const batchUpdate = useCallback((updates: Record<string, Partial<Agent>>) => {
    setAgents((prev) => prev.map((a) => {
      const u = updates[a.id]
      return u ? { ...a, ...u } : a
    }))
  }, [])

  const bubbleTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const showBubble = useCallback((aId: string, text: string, ttl: number = BUBBLE_TTL) => {
    const newBubble: SpeechBubble = {
      id: `b-${Date.now()}-${aId}`,
      agentId: aId,
      text,
      timestamp: new Date(),
    }
    setBubbles((prev) => [...prev.filter((b) => b.agentId !== aId), newBubble])

    // Auto-expire bubble
    const prev = bubbleTimers.current.get(aId)
    if (prev) clearTimeout(prev)
    bubbleTimers.current.set(aId, setTimeout(() => {
      setBubbles((p) => p.filter((b) => b.agentId !== aId))
      bubbleTimers.current.delete(aId)
    }, ttl))
  }, [])

  const clearBubbles = useCallback(() => {
    setBubbles([])
    bubbleTimers.current.forEach((t) => clearTimeout(t))
    bubbleTimers.current.clear()
  }, [])

  /* ── Boss call handler (works even when director is busy) ── */
  const handleBossCall = useCallback((targetName: string) => {
    const cur = agentsRef.current

    if (!targetName.trim()) {
      showBubble(DIRECTOR_ID, '叫誰？🤔', 3000)
      addLog(DIRECTOR_ID, '未指定員工名稱')
      return
    }

    // Find target by displayName (partial match) or id
    const target = cur.find(
      (a) =>
        a.id !== DIRECTOR_ID &&
        (a.displayName.includes(targetName) || a.id.includes(targetName) || a.name.includes(targetName)),
    )

    if (!target) {
      showBubble(DIRECTOR_ID, '找不到 🤷', 3000)
      addLog(DIRECTOR_ID, `找不到員工：${targetName}`)
      return
    }

    showBubble(DIRECTOR_ID, `${target.displayName}，來`, 3000)
    addLog(DIRECTOR_ID, `召喚 ${target.displayName} 到私密室`)

    setTimeout(() => {
      showBubble(target.id, '好的 😳', 3000)
    }, 1200)

    setTimeout(() => {
      batchUpdate({
        [DIRECTOR_ID]: { status: 'waiting', location: 'boss-room', currentTask: '私密會談中...', progress: undefined },
        [target.id]: { status: 'waiting', location: 'boss-room', currentTask: '私密會談中...', progress: undefined },
      })
      showBubble(DIRECTOR_ID, '🔒', 2500)

      setTimeout(() => {
        showBubble(target.id, '😳❤️', 3000)
      }, 2000)

      setTimeout(() => {
        batchUpdate({
          [DIRECTOR_ID]: { status: 'idle', location: undefined, currentTask: undefined },
          [target.id]: { status: 'idle', location: undefined, currentTask: undefined },
        })
        showBubble(DIRECTOR_ID, '回去吧 😏', 3000)
        showBubble(target.id, '......😊', 3000)
        addLog(DIRECTOR_ID, `與 ${target.displayName} 的私密會談結束`)
      }, 10000)
    }, 2500)
  }, [addLog, showBubble, batchUpdate])

  /* ── Tea time handler ── */
  const handleTeaTime = useCallback(() => {
    const cur = agentsRef.current
    const available = cur.filter((a) => (a.status === 'idle' || a.status === 'completed') && !a.location)

    if (available.length < 2) {
      showBubble(DIRECTOR_ID, '都在忙 😅', 3000)
      return
    }

    const count = Math.min(available.length, available.length >= 4 ? 2 + Math.floor(Math.random() * 3) : 2)
    const chosen = pickRandom(available, count)

    const names = chosen.map((a) => a.displayName).join('、')
    addLog('system', `${names} 去茶水間休息`)

    chosen.forEach((a, i) => {
      setTimeout(() => showBubble(a.id, '☕', 3000), i * 400)
    })

    setTimeout(() => {
      const updates: Record<string, Partial<Agent>> = {}
      chosen.forEach((a) => {
        updates[a.id] = { status: 'waiting', location: 'tea-room', currentTask: '休息中 ☕', progress: undefined }
      })
      batchUpdate(updates)

      setTimeout(() => {
        const speaker = randomItem(chosen)
        showBubble(speaker.id, randomItem(['好喝 ☕', '休息~', '😊']), 3000)
      }, 4000)

      setTimeout(() => {
        const clearUpdates: Record<string, Partial<Agent>> = {}
        chosen.forEach((a) => {
          clearUpdates[a.id] = { status: 'idle', location: undefined, currentTask: undefined }
        })
        batchUpdate(clearUpdates)
        const speaker = randomItem(chosen)
        showBubble(speaker.id, '回去了 💪', 3000)
      }, 12000)
    }, 1800)
  }, [addLog, batchUpdate, showBubble])

  /* ── sendCommand: external command handler ── */
  const sendCommand = useCallback((command: string, params: Record<string, string> = {}) => {
    if (command === 'bosscall') {
      handleBossCall(params.target ?? '')
    } else if (command === 'teatime') {
      handleTeaTime()
    }
  }, [handleBossCall, handleTeaTime])

  /* ── Mission lifecycle ── */

  useEffect(() => {
    let cancelled = false
    const timers: ReturnType<typeof setTimeout>[] = []
    let progressInterval: ReturnType<typeof setInterval> | null = null
    let autoTeaTimer: ReturnType<typeof setTimeout> | null = null
    let idleChatTimer: ReturnType<typeof setTimeout> | null = null

    function sched(fn: () => void, ms: number) {
      if (cancelled) return
      const t = setTimeout(() => { if (!cancelled) fn() }, ms)
      timers.push(t)
    }

    function schedAutoTea() {
      if (cancelled) return
      const delay = 25000 + Math.random() * 15000
      autoTeaTimer = setTimeout(() => {
        if (!cancelled) {
          handleTeaTime()
          schedAutoTea()
        }
      }, delay)
    }

    /* ═══════════════════════════════════════════
       氣泡策略分流
       ═══════════════════════════════════════════ */
    function schedIdleChat() {
      if (cancelled) return
      const delay = 5000 + Math.random() * 8000 // 5-13s 間距，比以前稀疏
      idleChatTimer = setTimeout(() => {
        if (cancelled) return
        const cur = agentsRef.current
        const idle = cur.filter((a) => a.status === 'idle' && !a.location)
        const working = cur.filter((a) => a.status === 'working')
        const hasActiveMission = missionActiveRef.current || working.length > 0

        if (hasActiveMission) {
          // ── 策略 1: 任務進行中 → 2~3 個閒置員工微反應 ──
          if (idle.length > 0) {
            const count = Math.min(idle.length, 2 + Math.floor(Math.random() * 2)) // 2~3
            const chosen = pickRandom(idle, count)
            chosen.forEach((a, i) => {
              sched(() => showBubble(a.id, randomItem(IDLE_MICRO_REACTIONS), 3000), i * 800)
            })
          }
        } else {
          // 計算閒置時間
          const idleMinutes = lastMissionEndRef.current > 0
            ? (Date.now() - lastMissionEndRef.current) / 60000
            : 999 // 第一次啟動視為已閒置

          if (idleMinutes >= 10 && idle.length >= 5) {
            // ── 策略 2: 閒置超過 10 分鐘 → 5 個員工辦公室日常 ──
            const chosen = pickRandom(idle, 5)
            chosen.forEach((a, i) => {
              sched(() => showBubble(a.id, randomItem(IDLE_OFFICE_CHAT), 4000), i * 1200)
            })
          } else if (idle.length > 0) {
            // 閒置未滿 10 分鐘 → 偶爾 1~2 個微反應
            if (Math.random() < 0.4) {
              const chosen = pickRandom(idle, Math.min(idle.length, 2))
              chosen.forEach((a, i) => {
                sched(() => showBubble(a.id, randomItem(IDLE_MICRO_REACTIONS), 3000), i * 600)
              })
            }
          }
        }

        schedIdleChat()
      }, delay)
    }

    function runMission() {
      if (cancelled) return
      missionActiveRef.current = true
      const mission = randomItem(MISSIONS)
      const names = mission.agentIds.map(agentName).join('、')

      // ═══ Phase 1: Director announces (0s) ═══
      showBubble(DIRECTOR_ID, '集合！', 3000)
      batchUpdate({
        [DIRECTOR_ID]: { status: 'working', currentTask: `指派任務：${mission.name}`, progress: undefined },
      })
      addLog(DIRECTOR_ID, `收到任務：${mission.name}，召集 ${names}`)

      // ═══ Phase 2: Agents gather (3.5s) ═══
      sched(() => {
        const updates: Record<string, Partial<Agent>> = {
          [DIRECTOR_ID]: { status: 'waiting', currentTask: '分配工作...' },
        }
        const responses = ['收到', '好的', '馬上', '了解', '來了', 'OK']
        mission.agentIds.forEach((id, i) => {
          updates[id] = { status: 'waiting', currentTask: '前往會議室...', progress: undefined }
          sched(() => showBubble(id, randomItem(responses), 2500), i * 500)
        })
        batchUpdate(updates)
      }, 3500)

      // ═══ Phase 3: Assign & start working (7.5s) ═══
      sched(() => {
        showBubble(DIRECTOR_ID, '開始！', 3000)
        addLog(DIRECTOR_ID, `分配 ${mission.name} 任務`)

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

        // ═══ Phase 3b: Progress ticking — 策略 3: 根據進度顯示氣泡 ═══
        let tickCount = 0
        progressInterval = setInterval(() => {
          if (cancelled) {
            if (progressInterval) clearInterval(progressInterval)
            return
          }
          tickCount++

          setAgents((prev) => prev.map((a) => {
            if (!mission.agentIds.includes(a.id) || a.status !== 'working' || a.progress === undefined) return a
            const inc = Math.random() * 14 + 4
            const newProgress = Math.min(100, Math.round(a.progress + inc))

            // ── 策略 3: 根據進度顯示任務階段氣泡 ──
            const labels = mission.progressLabels[a.id]
            if (labels) {
              const oldPhase = Math.min(Math.floor(a.progress / 25), 3)
              const newPhase = Math.min(Math.floor(newProgress / 25), 3)
              if (newPhase > oldPhase) {
                // 進入新階段，顯示對應的氣泡
                showBubble(a.id, labels[newPhase], 3500)
              }
            }

            return { ...a, progress: newProgress }
          }))

          // Check if all done
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
              showBubble(DIRECTOR_ID, '完成！👏', 4000)
              const updates: Record<string, Partial<Agent>> = {
                [DIRECTOR_ID]: { status: 'completed', currentTask: `${mission.name} 已完成` },
              }
              const doneReactions = ['完成 🎉', '搞定 ✅', '好了 😊', 'Done!', '✅']
              mission.agentIds.forEach((id, i) => {
                const task = mission.tasks[id] ?? '任務'
                updates[id] = { status: 'completed', currentTask: `已完成：${task}`, progress: 100 }
                addLog(id, `完成：${task}`, 'success')
                sched(() => showBubble(id, randomItem(doneReactions), 3000), i * 400)
              })
              addLog(DIRECTOR_ID, `${mission.name} 所有任務已完成`, 'success')
              batchUpdate(updates)

              // ═══ Phase 5: Walk back to desks ═══
              sched(() => {
                clearBubbles()
                const updates: Record<string, Partial<Agent>> = {
                  [DIRECTOR_ID]: { status: 'idle', currentTask: undefined, progress: undefined },
                }
                mission.agentIds.forEach((id) => {
                  updates[id] = { status: 'idle', currentTask: undefined, progress: undefined, collaboratingWith: undefined }
                })
                batchUpdate(updates)

                // 標記任務結束時間
                missionActiveRef.current = false
                lastMissionEndRef.current = Date.now()

                // ═══ Schedule next mission ═══
                sched(runMission, 6000 + Math.random() * 10000)
              }, 4000)
            }, 500)
          }, 80)
        }, 1500)
      }, 7500)
    }

    // Start first mission after 2s
    sched(runMission, 2000)
    // Start idle chatter
    schedIdleChat()
    // Start auto tea
    sched(schedAutoTea, 8000)

    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
      if (progressInterval) clearInterval(progressInterval)
      if (autoTeaTimer) clearTimeout(autoTeaTimer)
      if (idleChatTimer) clearTimeout(idleChatTimer)
      bubbleTimers.current.forEach((t) => clearTimeout(t))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { agents, rooms, workLogs, speechBubbles: bubbles, sendCommand }
}
