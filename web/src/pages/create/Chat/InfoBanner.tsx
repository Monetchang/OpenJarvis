import type { WorkflowEvent } from './types'

interface InfoBannerProps {
  event: WorkflowEvent
}

export default function InfoBanner({ event: _event }: InfoBannerProps) {
  return (
    <div className="my-2 rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
      已继续生成…
    </div>
  )
}
