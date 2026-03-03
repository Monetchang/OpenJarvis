import { useEffect, useRef } from 'react'
import type { ThinkingStream } from './utils/eventDisplay'
import { nodeNameLabel } from '../eventText'

interface ThinkingCardProps {
  stream: ThinkingStream
}

export default function ThinkingCard({ stream }: ThinkingCardProps) {
  const { node, sectionId, content } = stream
  const preRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    preRef.current?.scrollTo({ top: preRef.current.scrollHeight, behavior: 'smooth' })
  }, [content])

  const nodeLabel = nodeNameLabel(node)
  const title = sectionId ? `${nodeLabel} · ${sectionId}` : nodeLabel

  return (
    <div className="my-2 rounded border border-gray-200 bg-gray-50 overflow-hidden">
      <div className="px-3 py-2 text-sm text-gray-600 border-b border-gray-200">
        💭 {title}
      </div>
      <pre
        ref={preRef}
        className="text-xs text-gray-700 whitespace-pre-wrap break-words max-h-48 overflow-y-auto m-0 p-3 font-sans"
      >
        {content}
      </pre>
    </div>
  )
}
