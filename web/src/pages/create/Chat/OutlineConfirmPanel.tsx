import { useState, useEffect } from 'react'
import { Button, Card, Input } from 'antd'

export type OutlineSection = { id: string; title: string; [k: string]: unknown }
export type Outline = { sections?: OutlineSection[]; _artifact_id?: string; [k: string]: unknown }

interface OutlineConfirmPanelProps {
  outline: Outline
  outlineArtifactId?: string
  onConfirm: (outline: Outline, outlineArtifactId?: string) => void
  loading?: boolean
}

export default function OutlineConfirmPanel({
  outline,
  outlineArtifactId,
  onConfirm,
  loading = false,
}: OutlineConfirmPanelProps) {
  const sections = outline?.sections ?? []
  const [editedSections, setEditedSections] = useState<OutlineSection[]>(sections)

  useEffect(() => {
    setEditedSections(sections)
  }, [sections])

  const handleTitleChange = (idx: number, title: string) => {
    setEditedSections((prev) => {
      const next = [...prev]
      if (next[idx]) next[idx] = { ...next[idx], title }
      return next
    })
  }

  const handleConfirm = () => {
    const editedOutline: Outline = {
      ...outline,
      sections: editedSections.map((s) => ({ ...s, id: s.id, title: s.title })),
      _artifact_id: outline._artifact_id,
    }
    onConfirm(editedOutline, outlineArtifactId)
  }

  return (
    <Card title="确认大纲" size="small" className="mb-2">
      <div className="space-y-2 mb-3">
        {editedSections.map((sec, idx) => (
          <div key={sec.id ?? idx} className="flex items-center gap-2">
            <span className="text-gray-500 text-sm w-8">{idx + 1}.</span>
            <Input
              value={sec.title}
              onChange={(e) => handleTitleChange(idx, e.target.value)}
              placeholder="章节标题"
            />
          </div>
        ))}
      </div>
      <Button type="primary" onClick={handleConfirm} loading={loading}>
        确认并继续
      </Button>
    </Card>
  )
}
