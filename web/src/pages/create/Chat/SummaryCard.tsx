import type { WorkflowEvent } from './types'
import { renderSummary } from '../eventText'

interface SummaryCardProps {
  event: WorkflowEvent
  variant?: 'default' | 'highlight'
}

export default function SummaryCard({ event, variant = 'default' }: SummaryCardProps) {
  const text = renderSummary(event)
  const base = 'my-2 rounded border px-3 py-2 text-sm'
  const style =
    variant === 'highlight'
      ? 'border-amber-200 bg-amber-50 text-amber-800'
      : 'border-gray-200 bg-gray-50 text-gray-700'
  return <div className={`${base} ${style}`}>{text}</div>
}
