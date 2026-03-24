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

/** 泡泡自動消失時間 (ms) */
const BUBBLE_TTL = 5000

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

function agentName(id: string): string {
  return initialAgents.find((a) => a.id === id)?.displayName ?? id
}

let logSeq = initialWorkLogs.length + 1

/* ════════════════════════════════════════════
   Idle chatter — 待命時的隨機對話與表情
   ════════════════════════════════════════════ */

const IDLE_CHATTER: Record<string, string[]> = {
  'project-director':  ['今天進度不錯 👍', '來看看報告...', '☕ 先喝杯咖啡', '嗯...下個季度計畫...', '💼', '大家辛苦了！'],
  'research-lead':     ['這篇 paper 很有趣', '🤔 假設需要再驗證', '實驗數據看起來不錯', '📊', '跟學生約好 3 點開會'],
  'project-manager':   ['甘特圖更新完了', '📋 任務排好了', '下週的 sprint 要規劃', '會議紀錄寫完了 ✅', '🗓️'],
  'tech-lead':         ['code review 中...', '🔍 這段可以重構', '架構圖畫好了', 'CI 又紅了 😅', '💻'],
  'scada-processor':   ['資料匯入中... ⏳', '10min 均值計算完畢', 'Parquet 真好用', '📊 又一批新資料', '🔄'],
  'quality-checker':   ['品質分數 97.2% ✅', '這筆資料有點可疑...', '🔍 異常值偵測中', 'flag 標記完成', '✅'],
  'etl-engineer':      ['pipeline 跑完了', '🔧 修好那個 bug 了', 'Airflow DAG 更新', '☕ 等 job 跑完', '🔄'],
  'data-validator':    ['範圍檢查 pass ✅', '這個感測器的值怪怪的', '📐 校驗規則更新', '完整度 98.5%', '🛡️'],
  'stream-processor':  ['Kafka lag 正常', '🌊 串流穩定中', '每秒 3000 筆', '延遲 < 100ms 👍', '📡'],
  'storage-manager':   ['磁碟空間還夠', '💾 備份完成', '壓縮率 72%', '該清舊資料了...', '🗄️'],
  'metadata-curator':  ['標籤分類更新了', '🏷️ 新增 metadata 欄位', '索引重建中...', '分類標準化完成', '📝'],
  'pipeline-monitor':  ['所有 pipeline 正常 🟢', '⚠️ 有個 job 慢了', '監控面板刷新', '報警規則調整中', '📡'],
  'predictive-modeler':['loss 還在降 📉', '🤖 模型收斂了！', 'epoch 87/100...', 'RMSE 降到 2.8 了', 'GPU 溫度 72°C 😰'],
  'rag-architect':     ['向量搜尋好快 ⚡', '🔍 retrieval 準確率 93%', 'chunk size 調到 512', 'embedding 跑完了', '🧠'],
  'fault-diagnostician':['齒輪箱振動正常', '🔧 #3 號機要注意', '故障模式分析中', '預警等級：低 🟢', '⚠️'],
  'model-trainer':     ['訓練中... 🏋️', 'batch 256 效果不錯', 'checkpoint 存好了', '又要等 GPU 了 😴', '📈'],
  'experiment-tracker':['MLflow 記錄完成', '📈 這次 run 最好', '實驗 #42 結果出來了', 'metrics 已更新', '📊'],
  'hyperparameter-tuner':['Optuna 搜索中 🎛️', '找到更好的 lr 了！', '試過 200 組了...', '最佳組合更新', '🎯'],
  'feature-engineer':  ['新特徵計算完成', '🧬 特徵重要度排序', '風速^3 果然重要', 'PCA 降維中...', '📐'],
  'model-evaluator':   ['混淆矩陣看起來不錯', '📐 F1 score: 0.94', 'AUC 提升 2%', '交叉驗證跑完了', '✅'],
  'inference-deployer':['模型已部署 🚀', 'API 延遲 50ms', '版本 v2.3 上線', '負載測試通過', '🟢'],
  'anomaly-detector':  ['今天沒有異常 ✅', '🚨 偵測到微小偏移', '監控正常運行中', '閾值調整完成', '👀'],
  'iec-specialist':    ['IEC 61400 合規 ✅', '📜 標準更新了', '安全距離符合規定', '認證文件準備中', '⚖️'],
  'wake-analyst':      ['尾流效應 -8% 功率', '🌀 模擬跑完了', 'Jensen 模型對比中', '風場佈局優化', '🌬️'],
  'power-curve-expert':['功率曲線擬合完成', '📉 偏差在 2% 內', 'Cp 值計算中', '額定風速 12 m/s', '⚡'],
  'maintenance-planner':['下次維護：4/15', '🔩 備件清單更新', '預防性維護排程', '成本估算完成', '📋'],
  'wind-resource-analyst':['年均風速 7.2 m/s', '🌬️ Weibull k=2.1', '風花圖更新了', '發電量預估中', '📊'],
  'regulatory-advisor':['環評報告審查中', '⚖️ 法規合規 OK', '噪音標準符合', '鳥類衝擊評估', '📜'],
  'backend-dev':       ['API 寫好了 ✅', '🖥️ debug 中...', 'PostgreSQL 查詢優化', '又是 500 error 😤', '💻'],
  'frontend-dev':      ['元件 render 太多次 😩', '🎨 CSS 調好了', 'React 真香', '圖表動畫完成 ✨', '🖌️'],
  'devops-engineer':   ['Docker build 成功 🐳', '🔧 CI/CD 修好了', 'deploy 中...', 'k8s pod 重啟了', '☁️'],
  'api-designer':      ['OpenAPI spec 更新', '🔌 endpoint 設計好了', 'REST vs GraphQL...', '文件寫好了', '📄'],
  'database-admin':    ['查詢最佳化 -40% ⚡', '🗄️ 索引重建完成', '備份已排程', '連線池調整', '💾'],
  'test-engineer':     ['所有測試通過 ✅', '🧪 覆蓋率 87%', '發現一個 edge case', 'E2E 跑完了', '🐛'],
  'security-analyst':  ['安全掃描正常 🔒', '🛡️ 漏洞已修補', 'OWASP 檢查通過', '權限設定更新', '🔐'],
  'infra-manager':     ['伺服器負載正常', '☁️ 成本報告出來了', '擴容方案準備好', '監控告警正常', '📡'],
  'paper-writer':      ['寫到第三章了 ✏️', '📝 這段要改措辭', '引用格式統一中', '字數已達 5000', '☕ 寫論文好累'],
  'literature-reviewer':['又找到一篇好論文！', '📚 文獻庫更新', '這作者發了好多篇', '引用數統計中', '🔍'],
  'teaching-assistant':['作業批改中 📝', '🎓 學生問題好多', '教材更新完成', '下午要上課', '✏️'],
  'rag-curator':       ['新增 50 篇文獻', '📦 索引更新中', '分類標籤整理', '知識庫擴充完成', '🏷️'],
  'report-generator':  ['月報產生中...', '📄 圖表插入完成', '數據視覺化 OK', '報告匯出 PDF', '📊'],
  'data-storyteller':  ['這個趨勢很有趣 🤔', '📢 故事線整理好了', '視覺化敘事設計中', '簡報做好了', '🎯'],
}

/** 兩人閒聊對話組 */
const IDLE_CONVERSATIONS: Array<{ a: string; b: string; lines: [string, string] }> = [
  { a: 'paper-writer', b: 'literature-reviewer', lines: ['這篇 reference 幫我確認一下？', '沒問題，我查查看 📚'] },
  { a: 'frontend-dev', b: 'backend-dev', lines: ['API 回傳格式可以改嗎？', '什麼格式？跟我說 🤔'] },
  { a: 'model-trainer', b: 'hyperparameter-tuner', lines: ['lr=0.001 好像太大了', '我再跑一組試試 🎛️'] },
  { a: 'predictive-modeler', b: 'fault-diagnostician', lines: ['#7 號機的資料你看了嗎？', '看了，振動頻率有異常 ⚠️'] },
  { a: 'scada-processor', b: 'quality-checker', lines: ['新資料匯入了喔', '好，我來檢查品質 ✅'] },
  { a: 'project-director', b: 'research-lead', lines: ['下季度計畫寫好了嗎？', '快好了，明天給你 📋'] },
  { a: 'devops-engineer', b: 'test-engineer', lines: ['CI 怎麼又紅了？', '有個 flaky test 😅'] },
  { a: 'rag-architect', b: 'rag-curator', lines: ['新文獻 embedding 完了嗎？', '剛跑完，recall 提升了 👍'] },
  { a: 'wake-analyst', b: 'wind-resource-analyst', lines: ['這個風場佈局你覺得怎樣？', '間距可以再大一點 🌬️'] },
  { a: 'teaching-assistant', b: 'paper-writer', lines: ['學生問我論文怎麼寫...', '叫他先看我的範本 📝'] },
  { a: 'database-admin', b: 'storage-manager', lines: ['空間快不夠了 😰', '我來清理舊備份 💾'] },
  { a: 'security-analyst', b: 'infra-manager', lines: ['這個 port 要關掉', '好，防火牆更新 🔒'] },
  { a: 'project-manager', b: 'tech-lead', lines: ['sprint 進度如何？', '還差兩個 ticket 💻'] },
  { a: 'experiment-tracker', b: 'model-evaluator', lines: ['run #42 的 metrics 出來了', 'F1 看起來不錯 📊'] },
  { a: 'power-curve-expert', b: 'maintenance-planner', lines: ['功率偏差超過 3% 了', '排個檢修時間 🔩'] },
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
      showBubble(DIRECTOR_ID, '要叫誰來？請指定員工名稱 🤔', 4000)
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
      showBubble(DIRECTOR_ID, `找不到「${targetName}」這位員工 🤷`, 4000)
      addLog(DIRECTOR_ID, `找不到員工：${targetName}`)
      return
    }

    // Director bubble + target responds
    showBubble(DIRECTOR_ID, `${target.displayName}，來我辦公室一下 ❤️`, 3500)
    addLog(DIRECTOR_ID, `召喚 ${target.displayName} 到私密室`)

    setTimeout(() => {
      showBubble(target.id, '好...好的老闆 😳', 3000)
    }, 1200)

    setTimeout(() => {
      batchUpdate({
        [DIRECTOR_ID]: { status: 'waiting', location: 'boss-room', currentTask: '私密會談中...', progress: undefined },
        [target.id]: { status: 'waiting', location: 'boss-room', currentTask: '私密會談中...', progress: undefined },
      })
      showBubble(DIRECTOR_ID, '🔒 門已鎖上', 3000)

      setTimeout(() => {
        showBubble(target.id, '😳❤️', 3000)
      }, 2000)

      setTimeout(() => {
        batchUpdate({
          [DIRECTOR_ID]: { status: 'idle', location: undefined, currentTask: undefined },
          [target.id]: { status: 'idle', location: undefined, currentTask: undefined },
        })
        showBubble(DIRECTOR_ID, '好了，回去工作吧 😏', 4000)
        showBubble(target.id, '......😊', 4000)
        addLog(DIRECTOR_ID, `與 ${target.displayName} 的私密會談結束`)
      }, 10000)
    }, 2500)
  }, [addLog, showBubble, batchUpdate])

  /* ── Tea time handler (picks from idle OR completed agents) ── */
  const handleTeaTime = useCallback(() => {
    const cur = agentsRef.current
    // Allow idle or completed agents (not those already in a special room)
    const available = cur.filter((a) => (a.status === 'idle' || a.status === 'completed') && !a.location)

    if (available.length < 2) {
      showBubble(DIRECTOR_ID, '大家都在忙，沒人能去休息 😅', 4000)
      return
    }

    // Pick 2-4 random agents
    const shuffled = [...available].sort(() => Math.random() - 0.5)
    const count = Math.min(shuffled.length, available.length >= 4 ? 2 + Math.floor(Math.random() * 3) : 2)
    const chosen = shuffled.slice(0, count)

    const names = chosen.map((a) => a.displayName).join('、')
    addLog('system', `${names} 去茶水間休息`)

    // Show excited bubbles
    const teaEmoji = ['☕ 泡茶去！', '休息一下～ 🍪', '走走走！☕', '終於可以休息了 😊']
    chosen.forEach((a, i) => {
      setTimeout(() => showBubble(a.id, randomItem(teaEmoji), 4000), i * 400)
    })

    setTimeout(() => {
      const updates: Record<string, Partial<Agent>> = {}
      chosen.forEach((a) => {
        updates[a.id] = { status: 'waiting', location: 'tea-room', currentTask: '休息中 ☕', progress: undefined }
      })
      batchUpdate(updates)

      // Chat while in tea room
      setTimeout(() => {
        const teaChat = ['這個餅乾不錯 🍪', '你聽說了嗎...', '最近好忙啊 😮‍💨', '哈哈哈 😂', '老闆今天心情如何？', '週五要聚餐嗎？🍻']
        const speaker = randomItem(chosen)
        showBubble(speaker.id, randomItem(teaChat), 4000)
      }, 4000)

      setTimeout(() => {
        const clearUpdates: Record<string, Partial<Agent>> = {}
        chosen.forEach((a) => {
          clearUpdates[a.id] = { status: 'idle', location: undefined, currentTask: undefined }
        })
        batchUpdate(clearUpdates)
        // Show return bubbles
        const returnMsg = ['回去工作了 💪', '充電完畢 ⚡', '好，繼續！', '休息夠了 👍']
        const speaker = randomItem(chosen)
        showBubble(speaker.id, randomItem(returnMsg), 3000)
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
      const delay = 25000 + Math.random() * 15000 // ~25-40s
      autoTeaTimer = setTimeout(() => {
        if (!cancelled) {
          handleTeaTime()
          schedAutoTea()
        }
      }, delay)
    }

    /* ── Idle chatter: random bubbles from idle agents ── */
    function schedIdleChat() {
      if (cancelled) return
      const delay = 3000 + Math.random() * 5000 // 3-8s
      idleChatTimer = setTimeout(() => {
        if (cancelled) return
        const cur = agentsRef.current
        const idleAgents = cur.filter((a) => a.status === 'idle' && !a.location)

        if (idleAgents.length > 0) {
          // 30% chance of a 2-person conversation, 70% solo chatter
          if (Math.random() < 0.3 && idleAgents.length >= 2) {
            // Try to find a matching conversation pair
            const available = IDLE_CONVERSATIONS.filter(
              (c) => idleAgents.some((a) => a.id === c.a) && idleAgents.some((a) => a.id === c.b),
            )
            if (available.length > 0) {
              const conv = randomItem(available)
              showBubble(conv.a, conv.lines[0], 5000)
              sched(() => showBubble(conv.b, conv.lines[1], 5000), 1500)
            } else {
              // Fallback: random solo
              const agent = randomItem(idleAgents)
              const lines = IDLE_CHATTER[agent.id]
              if (lines) showBubble(agent.id, randomItem(lines), 4500)
            }
          } else {
            const agent = randomItem(idleAgents)
            const lines = IDLE_CHATTER[agent.id]
            if (lines) showBubble(agent.id, randomItem(lines), 4500)
          }
        }

        schedIdleChat()
      }, delay)
    }

    function runMission() {
      if (cancelled) return
      const mission = randomItem(MISSIONS)
      const names = mission.agentIds.map(agentName).join('、')

      // ═══ Phase 1: Director announces (0s) ═══
      const announcement = `收到任務！請${names}到會議室集合。`
      showBubble(DIRECTOR_ID, announcement, 4000)
      batchUpdate({
        [DIRECTOR_ID]: { status: 'working', currentTask: `指派任務：${mission.name}`, progress: undefined },
      })
      addLog(DIRECTOR_ID, announcement)

      // ═══ Phase 2: Agents gather (3.5s) ═══
      sched(() => {
        const updates: Record<string, Partial<Agent>> = {
          [DIRECTOR_ID]: { status: 'waiting', currentTask: '前往會議室主持...' },
        }
        const responses = ['收到！', '好的 👍', '馬上到！', '了解 🫡', '來了來了', 'OK 👌']
        mission.agentIds.forEach((id, i) => {
          updates[id] = { status: 'waiting', currentTask: '前往會議室...', progress: undefined }
          // Stagger response bubbles
          sched(() => showBubble(id, randomItem(responses), 3000), i * 600)
        })
        batchUpdate(updates)
        addLog(DIRECTOR_ID, `召集${names}前往會議室`)
      }, 3500)

      // ═══ Phase 3: Assign & start working (7.5s) ═══
      sched(() => {
        showBubble(DIRECTOR_ID, `${mission.name}：開始分配工作！`, 4000)
        addLog(DIRECTOR_ID, `開始分配 ${mission.name} 任務`)

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

        // Show agents acknowledging their tasks
        sched(() => {
          const ack = ['開始處理 💪', '沒問題！', '我來搞定 🔥', '進行中...', '馬上開始 ⚡']
          const speaker = randomItem(mission.agentIds)
          showBubble(speaker, randomItem(ack), 3500)
        }, 1500)

        // ═══ Phase 3b: Progress ticking ═══
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
            return { ...a, progress: Math.min(100, Math.round(a.progress + inc)) }
          }))

          // Occasional progress chatter during work
          if (tickCount % 3 === 0) {
            const progressChat = ['進度不錯 👍', '快好了...', '這邊有點卡 🤔', '再一下下！', '數據看起來 OK']
            const speaker = randomItem(mission.agentIds)
            showBubble(speaker, randomItem(progressChat), 3500)
          }

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
              showBubble(DIRECTOR_ID, `${mission.name} 全部完成，辛苦了！👏`, 5000)
              const updates: Record<string, Partial<Agent>> = {
                [DIRECTOR_ID]: { status: 'completed', currentTask: `${mission.name} 已完成` },
              }
              const doneReactions = ['完成了！🎉', '搞定 ✅', '終於好了 😊', 'Done! 💪', '太好了！']
              mission.agentIds.forEach((id, i) => {
                const task = mission.tasks[id] ?? '任務'
                updates[id] = { status: 'completed', currentTask: `已完成：${task}`, progress: 100 }
                addLog(id, `完成：${task}`, 'success')
                sched(() => showBubble(id, randomItem(doneReactions), 4000), i * 500)
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

                // ═══ Schedule next mission ═══
                sched(runMission, 6000 + Math.random() * 10000)
              }, 4000) // walk back
            }, 500) // brief pause
          }, 80) // let state settle
        }, 1500) // progress tick interval
      }, 7500) // announce + gather duration
    }

    // Start first mission after 2s
    sched(runMission, 2000)
    // Start idle chatter immediately
    schedIdleChat()
    // Start auto tea with a longer initial delay
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
