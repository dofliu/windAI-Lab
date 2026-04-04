import { useState, useEffect, useCallback, useRef } from 'react'
import { Agent, WorkLog, OfficeRoom, AgentStatus, SpeechBubble, WorkflowRetryEvent, WorkflowDegradationEvent, WorkflowCheckpointEvent } from '../types/agent'
import { initialRooms } from '../utils/mockData'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface WebSocketMessage {
  type: string
  timestamp: string
  payload: any
}

export function useWebSocket() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [rooms, setRooms] = useState<OfficeRoom[]>(initialRooms)
  const [workLogs, setWorkLogs] = useState<WorkLog[]>([])
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting')
  const [hasLiveUpdates, setHasLiveUpdates] = useState(false)
  const [fileEvents, setFileEvents] = useState<any[]>([])
  const [analysisResults, setAnalysisResults] = useState<any[]>([])
  const [workflowEvents, setWorkflowEvents] = useState<Array<WorkflowRetryEvent | WorkflowDegradationEvent | WorkflowCheckpointEvent>>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

  const updateRoomsFromAgents = useCallback((agentList: Agent[]) => {
    setRooms(prev => prev.map(room => ({
      ...room,
      agents: agentList.filter(a => a.tier === room.tier),
    })))
  }, [])

  // Convert backend snake_case agent to frontend camelCase
  const mapAgent = useCallback((raw: any): Agent => ({
    id: raw.id,
    name: raw.name,
    displayName: raw.display_name,
    tier: raw.tier,
    status: raw.status as AgentStatus,
    currentTask: raw.current_task || undefined,
    progress: raw.progress != null ? Math.round(raw.progress * 100) : undefined,
    collaboratingWith: raw.collaborating_with?.length ? raw.collaborating_with : undefined,
    color: raw.color,
    icon: raw.icon,
  }), [])

  const mapWorkLog = useCallback((raw: any): WorkLog => ({
    id: raw.id,
    timestamp: new Date(raw.timestamp),
    agentId: raw.agent_id,
    agentName: raw.agent_name,
    message: raw.message,
    type: raw.type,
  }), [])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus('connecting')
    const ws = new WebSocket('ws://localhost:8000/ws')

    ws.onopen = () => {
      setConnectionStatus('connected')
      console.log('WebSocket 已連線')
    }

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data)

        switch (msg.type) {
          case 'initial_state': {
            const agentList = (msg.payload.agents || []).map(mapAgent)
            setAgents(agentList)
            updateRoomsFromAgents(agentList)
            break
          }

          case 'agent_status_update': {
            setHasLiveUpdates(true)
            const updatedAgent = mapAgent(msg.payload)
            setAgents(prev => {
              const next = prev.map(a => a.id === updatedAgent.id ? updatedAgent : a)
              updateRoomsFromAgents(next)
              return next
            })
            break
          }

          case 'work_log_entry': {
            const logEntry = mapWorkLog(msg.payload)
            setWorkLogs(prev => {
              const next = [...prev, logEntry]
              return next.length > 200 ? next.slice(-200) : next
            })
            break
          }

          case 'task_progress': {
            const { agent_id, progress } = msg.payload
            setAgents(prev => {
              const next = prev.map(a =>
                a.id === agent_id
                  ? { ...a, progress: Math.round(progress * 100) }
                  : a
              )
              updateRoomsFromAgents(next)
              return next
            })
            break
          }

          case 'analysis_result': {
            setAnalysisResults(prev => {
              const next = [...prev, msg.payload]
              return next.length > 30 ? next.slice(-30) : next
            })
            break
          }

          case 'wind_farm_alert':
          case 'auto_dispatch': {
            setWorkflowEvents(prev => {
              const next = [...prev, msg.payload]
              return next.length > 50 ? next.slice(-50) : next
            })
            break
          }

          case 'file_detected':
          case 'file_processed':
          case 'file_error': {
            setFileEvents(prev => {
              const next = [...prev, msg.payload]
              return next.length > 50 ? next.slice(-50) : next
            })
            break
          }

          case 'workflow_retry':
          case 'workflow_degradation':
          case 'workflow_checkpoint': {
            setWorkflowEvents(prev => {
              const next = [...prev, msg.payload]
              return next.length > 50 ? next.slice(-50) : next
            })
            break
          }

          case 'agent_hired': {
            const newAgent = mapAgent(msg.payload)
            setAgents(prev => {
              // Replace if exists (offline→idle), or add new
              const exists = prev.some(a => a.id === newAgent.id)
              const next = exists
                ? prev.map(a => a.id === newAgent.id ? newAgent : a)
                : [...prev, newAgent]
              updateRoomsFromAgents(next)
              return next
            })
            break
          }

          case 'agent_fired': {
            const firedId = msg.payload.agent_id
            setAgents(prev => {
              const next = prev.map(a =>
                a.id === firedId ? { ...a, status: 'idle' as const, currentTask: undefined } : a
              ).filter(a => a.id !== firedId)
              updateRoomsFromAgents(next)
              return next
            })
            break
          }
        }
      } catch (e) {
        console.error('WebSocket 訊息解析失敗:', e)
      }
    }

    ws.onclose = () => {
      setConnectionStatus('disconnected')
      console.log('WebSocket 已斷線，5 秒後重連...')
      reconnectTimeoutRef.current = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      setConnectionStatus('error')
      ws.close()
    }

    wsRef.current = ws
  }, [mapAgent, mapWorkLog, updateRoomsFromAgents])

  const sendCommand = useCallback((command: string, parameters: Record<string, string> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // 注意：不再於此自動清除 analysisResults
      // 由 App.tsx 在任務記錄存檔後手動呼叫 clearAnalysisResults
      wsRef.current.send(JSON.stringify({
        type: 'execute_command',
        command,
        parameters,
      }))
    }
  }, [])

  const clearAnalysisResults = useCallback(() => setAnalysisResults([]), [])
  const clearWorkflowEvents = useCallback(() => setWorkflowEvents([]), [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const speechBubbles: SpeechBubble[] = [] // TODO: parse from WebSocket messages
  return { agents, rooms, workLogs, speechBubbles, connectionStatus, hasLiveUpdates, sendCommand, fileEvents, analysisResults, clearAnalysisResults, workflowEvents, clearWorkflowEvents }
}
