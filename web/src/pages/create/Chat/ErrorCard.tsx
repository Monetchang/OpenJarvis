import { useState } from 'react'
import type { WorkflowEvent } from './types'

interface ErrorCardProps {
  event: WorkflowEvent
}

export default function ErrorCard({ event }: ErrorCardProps) {
  const payload = event.payload ?? {}
  const action = (payload.action as string) ?? ''
  const reason = (payload.reason as string) ?? '未知错误'
  const idempotencyKey = (payload.idempotency_key as string) ?? ''
  const [showKey, setShowKey] = useState(false)

  return (
    <div className="my-2 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
      <div className="font-medium">操作被拒绝或失败</div>
      {action && <div>动作：{action}</div>}
      <div>{reason}</div>
      {idempotencyKey && (
        <div className="mt-1">
          <button
            type="button"
            className="text-xs text-red-600 underline"
            onClick={() => setShowKey((k) => !k)}
          >
            {showKey ? '隐藏' : '显示'} idempotency_key
          </button>
          {showKey && <pre className="mt-0.5 text-xs break-all">{idempotencyKey}</pre>}
        </div>
      )}
    </div>
  )
}
