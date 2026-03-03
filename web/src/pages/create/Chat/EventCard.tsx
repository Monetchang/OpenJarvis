import type { WorkflowEvent } from './types'
import { renderSummary } from '../eventText'

interface EventCardProps {
  event: WorkflowEvent
}

export default function EventCard({ event }: EventCardProps) {
  const text = renderSummary(event)
  const isUnknown = ![
    'stage.waiting_user', 'stage.started', 'stage.scheduled', 'stage.completed',
    'graph.started', 'graph.resumed', 'graph.completed', 'graph.failed',
    'workflow.configured', 'node.started', 'node.completed', 'node.failed',
    'artifact.created', 'action.ack', 'user_action.applied',
  ].includes(event.type)
  const display = isUnknown ? `系统事件：${event.type}` : text
  return (
    <div className="my-2 rounded border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
      {display}
    </div>
  )
}
