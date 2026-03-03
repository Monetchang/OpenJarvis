import { useState } from 'react'
import { Collapse } from 'antd'
import type { WorkflowEvent } from './types'
import { renderSummary } from '../eventText'

const SHOW_DEBUG_EVENTS = import.meta.env.VITE_DEBUG_EVENTS === 'true'

interface SystemDetailsProps {
  events: WorkflowEvent[]
  allEvents?: WorkflowEvent[]
}

function DebugEventRow({ event }: { event: WorkflowEvent }) {
  const [expanded, setExpanded] = useState(false)
  const summary = renderSummary(event)
  return (
    <div className="border-b border-gray-100 last:border-0 py-1">
      <div
        className="flex items-center justify-between cursor-pointer text-xs hover:bg-gray-50 rounded px-1"
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((x) => !x)}
      >
        <span className="text-gray-600">
          [{event.seq}] {event.type} — {summary}
        </span>
        <span className="text-gray-400 text-[10px]">{event.created_at?.slice(0, 19)}</span>
      </div>
      {expanded && (
        <pre className="mt-1 p-2 bg-gray-900 text-gray-100 text-[10px] overflow-x-auto rounded whitespace-pre-wrap break-all">
          {JSON.stringify({ type: event.type, seq: event.seq, payload: event.payload, created_at: event.created_at }, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default function SystemDetails({ events, allEvents }: SystemDetailsProps) {
  if (!SHOW_DEBUG_EVENTS) return null

  const debugEvents = (allEvents ?? events)
    .filter((e) => !e._optimistic && e.type !== 'llm.thinking')
    .sort((a, b) => a.seq - b.seq)
  if (debugEvents.length === 0) return null

  const debugPanel = (
    <div className="max-h-64 overflow-y-auto">
      {debugEvents.map((e) => (
        <DebugEventRow key={`${e.workflow_id}-${e.seq}`} event={e} />
      ))}
    </div>
  )

  return (
    <Collapse
      size="small"
      className="my-2"
      defaultActiveKey={[]}
      items={[{ key: 'debug', label: 'Debug（原始事件）', children: debugPanel }]}
    />
  )
}
