import type { WorkflowEvent } from './types'

interface SuccessBannerProps {
  event: WorkflowEvent
}

export default function SuccessBanner({ event: _event }: SuccessBannerProps) {
  return (
    <div className="my-2 rounded border border-green-300 bg-green-100 px-3 py-2 text-sm font-medium text-green-800">
      生成完成
    </div>
  )
}
