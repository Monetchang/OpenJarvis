import type { WorkflowEvent } from './types'

interface ChatBubbleProps {
  event: WorkflowEvent
}

export default function ChatBubble({ event }: ChatBubbleProps) {
  const role = (event.payload?.role as string) || 'user'
  const text = (event.payload?.text as string) || ''
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} my-2`}>
      <div
        className={`max-w-[75%] rounded-lg px-3 py-2 ${
          isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
        }`}
      >
        <div className="text-sm">{text}</div>
      </div>
    </div>
  )
}
