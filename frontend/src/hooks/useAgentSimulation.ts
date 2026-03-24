import { useState, useEffect, useCallback, useRef } from 'react'
import { Agent, WorkLog, OfficeRoom, AgentStatus } from '../types/agent'
import {
  initialAgents,
  initialRooms,
  initialWorkLogs,
  simulationTasks,
  simulationLogMessages,
} from '../utils/mockData'

let logCounter = initialWorkLogs.length + 1

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randomStatus(): AgentStatus {
  const statuses: AgentStatus[] = ['idle', 'working', 'working', 'working', 'waiting', 'completed']
  return randomItem(statuses)
}

export function useAgentSimulation() {
  const [agents, setAgents] = useState<Agent[]>(initialAgents)
  const [rooms, setRooms] = useState<OfficeRoom[]>(initialRooms)
  const [workLogs, setWorkLogs] = useState<WorkLog[]>(initialWorkLogs)
  const agentsRef = useRef(agents)

  agentsRef.current = agents

  const updateRooms = useCallback((updatedAgents: Agent[]) => {
    setRooms((prev) =>
      prev.map((room) => ({
        ...room,
        agents: updatedAgents.filter((a) => a.tier === room.tier),
      }))
    )
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setAgents((prev) => {
        // Pick 1-2 random agents to update
        const count = Math.random() > 0.5 ? 2 : 1
        const indices = new Set<number>()
        while (indices.size < count) {
          indices.add(Math.floor(Math.random() * prev.length))
        }

        const updated = prev.map((agent, i) => {
          if (!indices.has(i)) {
            // For working agents, bump progress slightly
            if (agent.status === 'working' && agent.progress !== undefined) {
              const newProgress = Math.min(100, agent.progress + Math.random() * 5)
              if (newProgress >= 100) {
                return { ...agent, status: 'completed' as AgentStatus, progress: 100 }
              }
              return { ...agent, progress: Math.round(newProgress) }
            }
            return agent
          }

          const newStatus = randomStatus()
          const tasks = simulationTasks[agent.id] ?? ['處理中...']

          const base: Partial<Agent> = {
            status: newStatus,
            currentTask: undefined,
            progress: undefined,
            collaboratingWith: undefined,
          }

          if (newStatus === 'working') {
            const otherAgents = prev.filter((a) => a.id !== agent.id)
            const collabCount = Math.random() > 0.6 ? 1 : 0
            const collabs = collabCount > 0
              ? [randomItem(otherAgents).id]
              : undefined

            return {
              ...agent,
              ...base,
              currentTask: randomItem(tasks),
              progress: Math.round(Math.random() * 60 + 5),
              collaboratingWith: collabs,
            }
          }

          if (newStatus === 'waiting') {
            return {
              ...agent,
              ...base,
              currentTask: randomItem(tasks),
              progress: Math.round(Math.random() * 40 + 50),
            }
          }

          if (newStatus === 'completed') {
            return {
              ...agent,
              ...base,
              currentTask: `已完成：${randomItem(tasks)}`,
            }
          }

          return { ...agent, ...base }
        })

        updateRooms(updated)
        return updated
      })
    }, 4000)

    return () => clearInterval(interval)
  }, [updateRooms])

  // Generate log entries
  useEffect(() => {
    const interval = setInterval(() => {
      const currentAgents = agentsRef.current
      const agent = randomItem(currentAgents)
      const messages = simulationLogMessages[agent.id] ?? ['正在處理任務...']
      const types: WorkLog['type'][] = ['info', 'info', 'info', 'success', 'warning']

      const newLog: WorkLog = {
        id: `log-${logCounter++}`,
        timestamp: new Date(),
        agentId: agent.id,
        agentName: agent.displayName,
        message: randomItem(messages),
        type: randomItem(types),
      }

      setWorkLogs((prev) => {
        const next = [...prev, newLog]
        // Keep last 100 entries
        return next.length > 100 ? next.slice(-100) : next
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  return { agents, rooms, workLogs }
}
