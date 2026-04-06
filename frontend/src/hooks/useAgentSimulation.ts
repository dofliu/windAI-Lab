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

/** 任務流程定義 — 只使用 12 個核心代理 */
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
    name: '功率曲線分析',
    agentIds: ['power-curve-expert', 'scada-processor', 'feature-engineer'],
    tasks: {
      'power-curve-expert': '訓練 NBM 功率曲線模型',
      'scada-processor': '載入清洗後的 SCADA 資料',
      'feature-engineer': '計算風速-功率特徵',
    },
    progressLabels: {
      'power-curve-expert': ['資料篩選', 'NBM 訓練', '偏差分析', '報告產出'],
      'scada-processor': ['讀取檔案', '格式轉換', '資料對齊', '輸出完成'],
      'feature-engineer': ['原始特徵', '衍生計算', '重要度排序', '輸出完成'],
    },
  },
  {
    name: '異常偵測分析',
    agentIds: ['anomaly-detector', 'scada-processor', 'maintenance-planner'],
    tasks: {
      'anomaly-detector': '執行多策略異常偵測',
      'scada-processor': '準備分析用資料集',
      'maintenance-planner': '根據結果排定維護計畫',
    },
    progressLabels: {
      'anomaly-detector': ['Z-score', 'IQR 偵測', 'IF 模型', '結果彙整'],
      'scada-processor': ['載入資料', '資料清洗', '特徵準備', '輸出完成'],
      'maintenance-planner': ['風險評估', '排程規劃', '資源分配', '計畫產出'],
    },
  },
  {
    name: 'RAG 知識庫更新',
    agentIds: ['rag-architect', 'paper-writer'],
    tasks: {
      'rag-architect': '優化向量檢索管線',
      'paper-writer': '整理新增文獻摘要',
    },
    progressLabels: {
      'rag-architect': ['分析查詢', '優化索引', '測試召回', '效能調校'],
      'paper-writer': ['文獻整理', '摘要撰寫', '格式校對', '索引更新'],
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
  // 表情符號
  '👀', '🤔', '💪', '👍', '☕', '😊', '💻', '🔍',
  '⚡', '🎯', '🌬️', '😄', '🙂', '😎', '🤗', '🫡',
  '✨', '🎵', '🌤️', '🍵', '🍰', '🎂', '🐱', '🐶',
  // 生活短句
  '嗯', '好的', '哈', '噢', 'OK', '嘿', '讚', '嗯嗯',
  '呵呵', '嘻嘻', '哇', '耶', '嗨', '呦', '唔', '哦哦',
  '好喔', '嘿嘿', '嗶嗶', '噗', '哼哼', '嘛', '是啊',
]

/* ════════════════════════════════════════════
   氣泡策略 2: 全場閒置 10 分鐘 — 辦公室日常對話
   隨機 5 個員工，氣泡文字 ≤5 字
   ════════════════════════════════════════════ */

const IDLE_OFFICE_CHAT: string[] = [
  // 天氣
  '好熱 ☀️', '下雨了 🌧️', '天氣好好', '涼涼的~', '起風了 🌬️', '好冷 🥶',
  // 飲食
  '午餐吃啥？', '肚子餓了', '☕ 喝咖啡', '來杯茶 🍵', '吃飽了~', '想吃甜的',
  '便當到了嗎', '要訂飲料嗎', '我要珍奶', '吃太撐了', '下午茶 🍰',
  // 辦公日常
  '好無聊...', '好想睡 😴', '快下班了', '週五了！', '又週一了',
  '休息一下', '伸展筋骨', '出去走走', '好累喔', '打個哈欠',
  '整理桌面', '回個信', '等消息中', '好的 👌', '還好嗎？',
  // 閒聊
  '加油加油', '看個新聞', '你們忙嗎', '嗯嗯', '😎',
  '💤', '今天還好嗎', '週末計畫？', '看劇了嗎', '好片推薦',
  '運動去！', '瑜伽好棒', '追劇中...', '逛街去~', '散步回來了',
  '聽音樂 🎵', '看書中 📖', '澆花 🌱', '好安靜喔', '打瞌睡~',
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
    addLog(DIRECTOR_ID, `召喚 ${target.displayName} 到小房間`)

    setTimeout(() => {
      showBubble(target.id, '好的 😳', 3000)
    }, 1200)

    setTimeout(() => {
      batchUpdate({
        [DIRECTOR_ID]: { status: 'waiting', location: 'boss-room', currentTask: '小房間會談中...', progress: undefined },
        [target.id]: { status: 'waiting', location: 'boss-room', currentTask: '小房間會談中...', progress: undefined },
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
        addLog(DIRECTOR_ID, `與 ${target.displayName} 的小房間會談結束`)
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

  /* ── Game time handler ── */
  const handleGameTime = useCallback(() => {
    const cur = agentsRef.current
    const available = cur.filter((a) => (a.status === 'idle' || a.status === 'completed') && !a.location)

    if (available.length < 2) {
      showBubble(DIRECTOR_ID, '沒人有空 😅', 3000)
      return
    }

    const count = Math.min(available.length, 2 + Math.floor(Math.random() * 2))
    const chosen = pickRandom(available, count)

    const names = chosen.map((a) => a.displayName).join('、')
    addLog('system', `${names} 去遊戲間打電動 🎮`)

    chosen.forEach((a, i) => {
      setTimeout(() => showBubble(a.id, '🎮', 3000), i * 300)
    })

    setTimeout(() => {
      const updates: Record<string, Partial<Agent>> = {}
      chosen.forEach((a) => {
        updates[a.id] = { status: 'waiting', location: 'game-room', currentTask: '打電動中 🎮', progress: undefined }
      })
      batchUpdate(updates)

      setTimeout(() => {
        const speaker = randomItem(chosen)
        showBubble(speaker.id, randomItem(['GG!', '贏了!', '再一場!', '😆', '太強了']), 3000)
      }, 4000)

      setTimeout(() => {
        const speaker = randomItem(chosen)
        showBubble(speaker.id, randomItem(['好玩!', '下次再來', '差點贏']), 3000)
      }, 8000)

      setTimeout(() => {
        const clearUpdates: Record<string, Partial<Agent>> = {}
        chosen.forEach((a) => {
          clearUpdates[a.id] = { status: 'idle', location: undefined, currentTask: undefined }
        })
        batchUpdate(clearUpdates)
        const speaker = randomItem(chosen)
        showBubble(speaker.id, '回去了 💪', 3000)
      }, 15000)
    }, 1800)
  }, [addLog, batchUpdate, showBubble])

  /* ── Quick mission trigger for slash commands ── */
  const triggerSlashMission = useCallback((command: string, turbineId: string) => {
    const missionMap: Record<string, { name: string; agents: string[]; tasks: Record<string, string> }> = {
      'diagnose': {
        name: `風機故障診斷 — ${turbineId}`,
        agents: ['project-director', 'fault-diagnostician', 'power-curve-expert', 'predictive-modeler', 'literature-reviewer', 'paper-writer'],
        tasks: {
          'project-director': `確認 ${turbineId} 任務範圍並分派`,
          'fault-diagnostician': '執行故障分類與異常偵測',
          'power-curve-expert': 'NBM 功率曲線建模',
          'predictive-modeler': 'RUL 壽命預測',
          'literature-reviewer': '搜索相關故障案例文獻',
          'paper-writer': '生成診斷報告',
        },
      },
      'monthly-review': {
        name: `月度健康評估 — ${turbineId}`,
        agents: ['project-director', 'scada-processor', 'quality-checker', 'fault-diagnostician', 'power-curve-expert', 'predictive-modeler', 'rag-architect', 'paper-writer'],
        tasks: {
          'project-director': `確認 ${turbineId} 月度評估範圍`,
          'scada-processor': '載入本月 SCADA 運轉資料',
          'quality-checker': '處理警報事件清單',
          'fault-diagnostician': '功率曲線偏差 + 故障分類',
          'power-curve-expert': 'NBM 健康分數評估',
          'predictive-modeler': '更新 RUL 壽命預測',
          'rag-architect': '嵌入運維月報 + 歷史案例比對',
          'paper-writer': '生成月度健康報告',
        },
      },
      'train-nbm': {
        name: `NBM 訓練 — ${turbineId}`,
        agents: ['project-director', 'power-curve-expert'],
        tasks: {
          'project-director': '確認並分派 NBM 訓練任務',
          'power-curve-expert': `訓練 ${turbineId} NBM 功率曲線模型`,
        },
      },
      'predict-rul': {
        name: `RUL 預測 — ${turbineId}`,
        agents: ['project-director', 'predictive-modeler'],
        tasks: {
          'project-director': '確認並分派 RUL 預測任務',
          'predictive-modeler': `預測 ${turbineId} 剩餘使用壽命`,
        },
      },
      'lit-search': {
        name: `文獻搜索`,
        agents: ['project-director', 'research-lead', 'literature-reviewer', 'paper-writer'],
        tasks: {
          'project-director': '確認文獻搜索範圍',
          'research-lead': '規劃搜索策略與關鍵字',
          'literature-reviewer': '搜索並篩選相關論文',
          'paper-writer': '整理文獻摘要',
        },
      },
      'data:load': {
        name: `資料載入 — ${turbineId}`,
        agents: ['project-director', 'scada-processor', 'quality-checker', 'feature-engineer'],
        tasks: {
          'project-director': '確認並分派資料載入任務',
          'scada-processor': `智慧載入 ${turbineId} SCADA 資料`,
          'quality-checker': '資料品質檢查與驗證',
          'feature-engineer': '自動特徵偵測與分析',
        },
      },
      'data:clean': {
        name: `資料清洗 — ${turbineId}`,
        agents: ['project-director', 'scada-processor', 'quality-checker'],
        tasks: {
          'project-director': '確認並分派資料清洗任務',
          'scada-processor': `清洗 ${turbineId} 資料（去重、插值）`,
          'quality-checker': '異常值過濾與品質報告',
        },
      },
      'ai:train': {
        name: `ML 訓練 — ${turbineId}`,
        agents: ['project-director', 'fault-diagnostician', 'predictive-modeler', 'experiment-tracker'],
        tasks: {
          'project-director': '確認並分派模型訓練任務',
          'fault-diagnostician': '故障分類器 + NBM 訓練',
          'predictive-modeler': 'RUL 退化模型擬合',
          'experiment-tracker': '記錄實驗結果至追蹤系統',
        },
      },
      'ai:evaluate': {
        name: `模型評估 — ${turbineId}`,
        agents: ['project-director', 'fault-diagnostician', 'predictive-modeler', 'paper-writer'],
        tasks: {
          'project-director': '確認並分派模型評估任務',
          'fault-diagnostician': 'NBM 殘差分析與異常偵測',
          'predictive-modeler': 'RUL 預測誤差評估',
          'paper-writer': '彙整效能評估報告',
        },
      },
    }

    const mission = missionMap[command]
    if (!mission) return

    // Director announces
    addLog('system', `指令 /${command} 已執行：${mission.name}`)
    showBubble(DIRECTOR_ID, `開始！`, 3000)

    // Activate agents
    setTimeout(() => {
      const updates: Record<string, Partial<Agent>> = {}
      mission.agents.forEach((id) => {
        updates[id] = {
          status: 'working',
          currentTask: mission.tasks[id] || '執行中...',
          progress: 0,
        }
      })
      batchUpdate(updates)

      // Progress simulation
      let prog = 0
      const progTimer = setInterval(() => {
        prog += 15 + Math.random() * 10
        if (prog >= 100) {
          clearInterval(progTimer)
          const doneUpdates: Record<string, Partial<Agent>> = {}
          mission.agents.forEach((id) => {
            doneUpdates[id] = { status: 'completed', progress: 100 }
          })
          batchUpdate(doneUpdates)
          addLog('system', `✅ ${mission.name} 完成`)
          showBubble(DIRECTOR_ID, '完成！👏', 3000)

          // Reset to idle after 5s
          setTimeout(() => {
            const resetUpdates: Record<string, Partial<Agent>> = {}
            mission.agents.forEach((id) => {
              resetUpdates[id] = { status: 'idle', currentTask: undefined, progress: undefined }
            })
            batchUpdate(resetUpdates)
          }, 5000)
        } else {
          const progUpdates: Record<string, Partial<Agent>> = {}
          mission.agents.forEach((id) => {
            progUpdates[id] = { progress: Math.round(Math.min(prog + Math.random() * 10, 99)) }
          })
          batchUpdate(progUpdates)
        }
      }, 2000)
    }, 1500)
  }, [addLog, showBubble, batchUpdate])

  /* ── sendCommand: external command handler ── */
  // 模擬指令使用 simu-* 前綴，與真實後端指令區隔
  const SIMU_COMMAND_MAP: Record<string, string> = {
    'simu-load': 'data:load',
    'simu-clean': 'data:clean',
    'simu-train': 'ai:train',
    'simu-evaluate': 'ai:evaluate',
    // 真實指令也可觸發模擬動畫（做為後端離線時的 fallback）
    'diagnose': 'diagnose',
    'monthly-review': 'monthly-review',
    'train-nbm': 'train-nbm',
    'predict-rul': 'predict-rul',
    'data:load': 'data:load',
    'data:clean': 'data:clean',
    'ai:train': 'ai:train',
    'ai:evaluate': 'ai:evaluate',
    'lit-search': 'lit-search',
  }

  const sendCommand = useCallback((command: string, params: Record<string, string> = {}) => {
    if (command === 'bosscall') {
      handleBossCall(params.target ?? '')
    } else if (command === 'teatime') {
      handleTeaTime()
    } else if (command === 'gametime') {
      handleGameTime()
    } else if (SIMU_COMMAND_MAP[command]) {
      triggerSlashMission(SIMU_COMMAND_MAP[command], params.turbine_id || 'WT-01')
    }
  }, [handleBossCall, handleTeaTime, handleGameTime, triggerSlashMission])

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

    // schedAutoTea 已停用 — 不再自動觸發茶歇/遊戲，僅由使用者手動指令
    // function schedAutoTea() { ... }

    /* ═══════════════════════════════════════════
       氣泡策略分流
       ═══════════════════════════════════════════ */
    function schedIdleChat() {
      if (cancelled) return
      const delay = 15000 + Math.random() * 15000 // 15-30s 間距，降低頻率
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

    // @ts-ignore: 保留任務邏輯供後端觸發使用
    function _runMission() {
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

                // ═══ Schedule next mission (disabled in simulation mode) ═══
                // sched(_runMission, 6000 + Math.random() * 10000)
              }, 4000)
            }, 500)
          }, 80)
        }, 1500)
      }, 7500)
    }

    // 模擬模式：不自動啟動任務，只保留心情狀態
    // 真正的任務由後端 orchestration engine 或 FileWatcher 觸發
    // sched(runMission, 2000)

    // Start idle chatter (心情氣泡)
    schedIdleChat()
    // 不再自動觸發茶歇/遊戲，僅由使用者手動 /teatime 或 /gametime 觸發
    // sched(schedAutoTea, 8000)

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
