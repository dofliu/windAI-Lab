import { Agent, OfficeRoom } from '../types/agent'
import { tierColors } from '../utils/mockData'
import AgentCard from './AgentCard'

interface OfficeFloorProps {
  rooms: OfficeRoom[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
}

export default function OfficeFloor({
  rooms,
  selectedAgent,
  onSelectAgent,
}: OfficeFloorProps) {
  return (
    <div className="grid auto-rows-fr gap-4 p-4 md:grid-cols-2">
      {rooms.map((room) => {
        const colors = tierColors[room.tier] ?? tierColors['leadership']
        const workingCount = room.agents.filter(
          (a) => a.status === 'working'
        ).length

        return (
          <div
            key={room.id}
            className={`room-card ${colors.bg} border ${colors.border} flex flex-col`}
          >
            <div className="flex items-center justify-between border-b border-slate-700/40 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{room.icon}</span>
                <h3 className={`font-semibold ${colors.accent}`}>
                  {room.name}
                </h3>
              </div>
              <span className="text-xs text-slate-500">
                {workingCount > 0
                  ? `${workingCount} 位工作中`
                  : `${room.agents.length} 位成員`}
              </span>
            </div>

            <div className="flex flex-1 flex-col gap-1 p-2">
              {room.agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isSelected={selectedAgent?.id === agent.id}
                  onSelect={onSelectAgent}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
