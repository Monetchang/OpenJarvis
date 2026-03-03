import type { WorkflowEvent } from './types'

interface StageStatusCardProps {
  event: WorkflowEvent
}

export default function StageStatusCard({ event }: StageStatusCardProps) {
  const type = event.type
  const payload = event.payload ?? {}
  let label = '生成中…'
  if (type === 'stage.started') {
    const attempt = (payload.attempt as number) ?? 1
    label = attempt > 1 ? `继续生成（第 ${attempt} 次）` : '开始生成'
  } else if (type === 'workflow.configured') {
    const style = (payload.style as string) ?? ''
    const audience = (payload.audience as string) ?? ''
    label = style || audience ? `已配置：${[style, audience].filter(Boolean).join(' / ')}` : '已配置'
  }
  return (
    <div className="my-2 rounded border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
      {label}
    </div>
  )
}
