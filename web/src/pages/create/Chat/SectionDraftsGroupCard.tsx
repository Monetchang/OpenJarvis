import { useState, useEffect } from 'react'
import { Card } from 'antd'
import type { ArtifactMeta } from './types'
import { getArtifact } from '@/services/workflowApi'

interface SectionDraftsGroupCardProps {
  workflowId: string
  items: ArtifactMeta[]
}

function hasFullContent(a: ArtifactMeta): boolean {
  return !!(a.title || a.content_preview || a.content_json)
}

export default function SectionDraftsGroupCard({ workflowId, items }: SectionDraftsGroupCardProps) {
  const [open, setOpen] = useState(false)
  const [fetched, setFetched] = useState<Map<string, ArtifactMeta>>(new Map())

  useEffect(() => {
    if (!open || !workflowId) return
    const toFetch = items.filter((a) => !hasFullContent(a) && !fetched.has(a.artifact_id))
    if (toFetch.length === 0) return
    Promise.all(toFetch.map((a) => getArtifact(workflowId, a.artifact_id))).then((results) => {
      setFetched((prev) => {
        const next = new Map(prev)
        results.forEach((a) => {
          if (a) next.set(a.artifact_id, a)
        })
        return next
      })
    })
  }, [open, workflowId, items])

  const n = items.length
  if (n === 0) return null

  const previews = items.map((a) => {
    const full = fetched.get(a.artifact_id) ?? a
    const cj = full.content_json as { section_id?: string; content?: string } | undefined
    const title = full.title ?? cj?.section_id ?? full.scope_key ?? full.artifact_id
    const preview = full.content_preview ?? (typeof cj?.content === 'string' ? cj.content.slice(0, 100) + '…' : '')
    return { title, preview, artifact_id: full.artifact_id }
  })

  return (
    <Card size="small" className="my-2">
      <div
        className="text-sm text-gray-600 cursor-pointer select-none"
        onClick={() => setOpen((o) => !o)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setOpen((o) => !o)}
      >
        {open ? '收起' : '展开'} — 生成了 {n} 节草稿
      </div>
      {open && (
        <div className="mt-2 space-y-2">
          {previews.map((p, i) => (
            <div key={p.artifact_id ?? i} className="rounded border border-gray-100 bg-gray-50 px-2 py-1 text-xs">
              <div className="font-medium text-gray-700">{p.title}</div>
              <div className="text-gray-500 truncate">{p.preview}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
