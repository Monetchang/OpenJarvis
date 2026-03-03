import { useState, useEffect } from 'react'
import { Button, Card, Drawer, message } from 'antd'
import { DownloadOutlined, CopyOutlined, EyeOutlined } from '@ant-design/icons'
import type { ArtifactMeta } from './types'
import { getArtifact } from '@/services/workflowApi'

interface FinalArtifactCardProps {
  workflowId: string
  meta: ArtifactMeta
  articleTitle?: string
}

function getMarkdownFromMeta(meta: ArtifactMeta): string | null {
  const cj = meta.content_json
  if (!cj) return null
  const md = (cj as { markdown?: string }).markdown
  return typeof md === 'string' ? md : null
}

export default function FinalArtifactCard({ workflowId, meta, articleTitle }: FinalArtifactCardProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [fullContent, setFullContent] = useState<string | null>(getMarkdownFromMeta(meta))
  const [fetchedPreview, setFetchedPreview] = useState<string>('')
  const [previewLoading, setPreviewLoading] = useState(false)

  const preview = meta.content_preview ?? fetchedPreview
  const title = articleTitle ?? meta.title ?? `最终正文 (v${meta.version})`

  useEffect(() => {
    if (meta.content_preview) return
    if (!workflowId || !meta.artifact_id) return
    setPreviewLoading(true)
    getArtifact(workflowId, meta.artifact_id).then((a) => {
      if (!a) return
      if (a.content_preview) setFetchedPreview(a.content_preview)
      const md = (a.content_json as { markdown?: string })?.markdown
      if (typeof md === 'string') setFullContent(md)
    }).catch(() => {}).finally(() => setPreviewLoading(false))
  }, [workflowId, meta.artifact_id, meta.content_preview])

  const ensureContent = async (): Promise<string> => {
    if (fullContent) return fullContent
    const a = await getArtifact(workflowId, meta.artifact_id)
    if (!a?.content_json) throw new Error('无法获取内容')
    const md = (a.content_json as { markdown?: string }).markdown
    if (typeof md === 'string') {
      setFullContent(md)
      return md
    }
    throw new Error('无 markdown 内容')
  }

  const handleDownload = async () => {
    try {
      const text = await ensureContent()
      const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title.replace(/\s+/g, '_')}.md`
      a.click()
      URL.revokeObjectURL(url)
      message.success('已下载')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '下载失败')
    }
  }

  const handleCopy = async () => {
    try {
      const text = await ensureContent()
      await navigator.clipboard.writeText(text)
      message.success('已复制')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '复制失败')
    }
  }

  const handlePreview = () => {
    setDrawerOpen(true)
    if (!fullContent) ensureContent().then(setFullContent).catch(() => setFullContent(''))
  }

  return (
    <>
      <Card size="small" title={title} className="my-2">
        <div className="text-sm text-gray-600 whitespace-pre-wrap break-words mb-3 max-h-32 overflow-y-auto">
          {preview || (previewLoading ? '加载中…' : '（无预览）')}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="primary" size="small" icon={<DownloadOutlined />} onClick={handleDownload}>
            下载 Markdown
          </Button>
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>
            复制
          </Button>
          <Button size="small" icon={<EyeOutlined />} onClick={handlePreview}>
            预览
          </Button>
        </div>
      </Card>
      <Drawer title={title} open={drawerOpen} onClose={() => setDrawerOpen(false)} width="80%">
        <pre className="whitespace-pre-wrap text-sm font-sans">{fullContent ?? '加载中…'}</pre>
      </Drawer>
    </>
  )
}
