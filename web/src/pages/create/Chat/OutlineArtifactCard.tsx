import { useState, useEffect } from 'react'
import { Card, Button, Drawer } from 'antd'
import { EyeOutlined } from '@ant-design/icons'
import type { ArtifactMeta } from './types'
import { getArtifact } from '@/services/workflowApi'

interface OutlineArtifactCardProps {
  workflowId: string
  meta: ArtifactMeta
}

export default function OutlineArtifactCard({ workflowId, meta }: OutlineArtifactCardProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sections, setSections] = useState<{ id: string; title: string }[]>(() => {
    const outline = (meta.content_json as { sections?: { id: string; title: string }[] }) ?? {}
    return outline.sections ?? []
  })
  const [fetchedPreview, setFetchedPreview] = useState('')
  const [loading, setLoading] = useState(false)

  const title = meta.title ?? (meta.version <= 1 ? '大纲初稿' : '确认大纲')
  const rawPreview = meta.content_preview ?? fetchedPreview
  const isNoisyPreview = (s: string) =>
    !s ||
    s === 'Proposed outline' ||
    s.includes("'sections'") ||
    s.includes("{'") ||
    /^[\s\S]*\{[\s\S]*'id'[\s\S]*\}[\s\S]*$/.test(s)
  const preview = isNoisyPreview(rawPreview) ? '' : rawPreview

  useEffect(() => {
    if (meta.content_preview && (meta.content_json as { sections?: unknown[] })?.sections?.length) return
    if (!workflowId || !meta.artifact_id) return
    getArtifact(workflowId, meta.artifact_id).then((a) => {
      if (!a) return
      if (a.content_preview) setFetchedPreview(a.content_preview)
      const outline = (a.content_json as { sections?: { id: string; title: string }[] }) ?? {}
      if (outline.sections?.length) setSections(outline.sections)
    }).catch(() => {})
  }, [workflowId, meta.artifact_id, meta.content_preview])

  const handlePreview = async () => {
    setDrawerOpen(true)
    if (sections.length > 0) return
    setLoading(true)
    try {
      const a = await getArtifact(workflowId, meta.artifact_id)
      const outline = (a?.content_json as { sections?: { id: string; title: string }[] }) ?? {}
      setSections(outline.sections ?? [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Card size="small" title={title} className="my-2">
        {sections.length > 0 && (
          <div className="mb-2">
            <ul className="list-none pl-0 text-sm space-y-1">
              {sections.map((s, i) => (
                <li key={s.id ?? i}>
                  <span className="text-gray-500">{i + 1}.</span> {s.title || s.id || '—'}
                </li>
              ))}
            </ul>
          </div>
        )}
        {preview && (
          <div className="text-sm text-gray-600 whitespace-pre-wrap break-words max-h-20 overflow-y-auto mb-2">
            {preview}
          </div>
        )}
        <Button size="small" icon={<EyeOutlined />} onClick={handlePreview} loading={loading}>
          预览
        </Button>
      </Card>
      <Drawer title={title} open={drawerOpen} onClose={() => setDrawerOpen(false)} width="400">
        {loading ? (
          <span className="text-gray-500">加载中…</span>
        ) : (
          <ul className="list-none pl-0 text-sm space-y-2">
            {sections.map((s, i) => (
              <li key={s.id ?? i}>
                <span className="text-gray-500">{i + 1}.</span> {s.title || s.id || '—'}
              </li>
            ))}
          </ul>
        )}
      </Drawer>
    </>
  )
}
