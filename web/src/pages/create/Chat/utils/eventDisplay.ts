import type { WorkflowEvent, EventDisplayConfig, WorkflowUIState } from '../types'

const MAIN_TYPES = new Set([
  'chat.message',
  'stage.started',
  'stage.waiting_user',
  'graph.completed',
  'graph.resumed',
  'workflow.configured',
  'artifact.created',
])
const COLLAPSE_TYPES = new Set(['node.started', 'node.completed', 'stage.scheduled', 'graph.started'])
const ACK_HIGHLIGHT_STATUS = new Set(['REJECTED', 'FAILED'])

export function getDisplayConfig(type: string, payload: Record<string, unknown>): EventDisplayConfig {
  if (type === 'action.ack') {
    const status = (payload?.status as string) ?? ''
    if (ACK_HIGHLIGHT_STATUS.has(status)) {
      return { showInMain: true, priority: 'highlight', component: 'ErrorCard' }
    }
    return { showInMain: false, priority: 'collapse', component: 'SystemDetails' }
  }
  if (COLLAPSE_TYPES.has(type)) {
    return { showInMain: false, priority: 'collapse', component: 'SystemDetails' }
  }
  if (type === 'graph.resumed') {
    return { showInMain: true, priority: 'highlight', component: 'InfoBanner' }
  }
  if (type === 'stage.waiting_user') {
    return { showInMain: false, priority: 'collapse', component: 'SystemDetails' }
  }
  if (type === 'graph.completed') {
    return { showInMain: true, priority: 'highlight', component: 'SuccessBanner' }
  }
  if (type === 'stage.started' || type === 'workflow.configured') {
    return { showInMain: true, priority: 'normal', component: 'StageStatusCard' }
  }
  if (type === 'artifact.created') {
    const artifactType = (payload?.type as string) ?? ''
    if (artifactType === 'final_markdown') return { showInMain: true, priority: 'highlight', component: 'FinalArtifactCard' }
    if (artifactType === 'outline_plan') return { showInMain: true, priority: 'normal', component: 'OutlineArtifactCard' }
    if (artifactType === 'article_plan') return { showInMain: true, priority: 'normal', component: 'EventCard' }
    if (artifactType === 'section_draft') return { showInMain: true, priority: 'collapse', component: 'SectionDraftsGroupCard' }
    return { showInMain: true, priority: 'normal', component: 'EventCard' }
  }
  if (type === 'chat.message') {
    return { showInMain: true, priority: 'normal', component: 'ChatBubble' }
  }
  if (type === 'llm.thinking') {
    return { showInMain: false, priority: 'collapse', component: 'SystemDetails' }
  }
  if (MAIN_TYPES.has(type)) {
    return { showInMain: true, priority: 'normal', component: 'EventCard' }
  }
  return { showInMain: false, priority: 'collapse', component: 'SystemDetails' }
}

export function filterMainTimelineEvents(events: WorkflowEvent[]): WorkflowEvent[] {
  const sorted = [...events].filter((e) => !e._optimistic).sort((a, b) => a.seq - b.seq)
  const seen = new Set<number>()
  const out: WorkflowEvent[] = []
  for (const e of sorted) {
    if (seen.has(e.seq)) continue
    seen.add(e.seq)
    const config = getDisplayConfig(e.type, e.payload ?? {})
    if (config.showInMain) out.push(e)
  }
  return out
}

export function getSystemDetailEvents(events: WorkflowEvent[]): WorkflowEvent[] {
  const sorted = [...events].filter((e) => !e._optimistic).sort((a, b) => a.seq - b.seq)
  const seen = new Set<number>()
  const out: WorkflowEvent[] = []
  for (const e of sorted) {
    if (seen.has(e.seq)) continue
    seen.add(e.seq)
    const config = getDisplayConfig(e.type, e.payload ?? {})
    if (config.component === 'SystemDetails') out.push(e)
  }
  return out
}

export function deriveUIState(events: WorkflowEvent[]): WorkflowUIState {
  const sorted = [...events].filter((e) => !e._optimistic).sort((a, b) => a.seq - b.seq)
  let lastWaitingSeq = 0
  let lastResumedSeq = 0
  let lastCompletedSeq = 0
  let lastStartedSeq = 0
  let hasError = false

  for (const e of sorted) {
    if (e.type === 'stage.waiting_user') lastWaitingSeq = e.seq
    if (e.type === 'graph.resumed') lastResumedSeq = e.seq
    if (e.type === 'graph.completed') lastCompletedSeq = e.seq
    if (e.type === 'graph.started' || e.type === 'stage.started') lastStartedSeq = e.seq
    if (e.type === 'action.ack') {
      const s = (e.payload?.status as string) ?? ''
      if (ACK_HIGHLIGHT_STATUS.has(s)) hasError = true
    }
    if (e.type === 'graph.failed' || e.type === 'node.failed') hasError = true
  }

  if (hasError) return 'ERROR'
  if (lastWaitingSeq > 0 && lastWaitingSeq > lastResumedSeq && lastWaitingSeq > lastCompletedSeq) return 'WAITING_USER'
  if (lastCompletedSeq > 0 && lastCompletedSeq >= lastStartedSeq) return 'COMPLETED'
  if (lastStartedSeq > 0) return 'RUNNING'
  return 'IDLE'
}

export type ThinkingStream = {
  key: string
  node: string
  sectionId: string
  content: string
}

export function deriveThinkingStreams(events: WorkflowEvent[]): ThinkingStream[] {
  const sorted = [...events].filter((e) => !e._optimistic).sort((a, b) => a.seq - b.seq)
  const streams = new Map<string, { node: string; sectionId: string; content: string; complete: boolean }>()
  for (const e of sorted) {
    if (e.type !== 'llm.thinking') continue
    const p = e.payload ?? {}
    const node = (p.node as string) ?? ''
    const sectionId = (p.section_id as string) ?? ''
    const key = `${node}|${sectionId}`
    const chunk = (p.chunk as string) ?? ''
    const thinking = (p.thinking as string) ?? ''
    if (chunk) {
      const cur = streams.get(key)
      const nextContent = (cur?.content ?? '') + chunk
      streams.set(key, {
        node,
        sectionId,
        content: nextContent,
        complete: cur?.complete ?? false,
      })
    }
    if (thinking) {
      streams.set(key, {
        node,
        sectionId,
        content: thinking,
        complete: true,
      })
    }
  }
  return [...streams.entries()]
    .filter(([, s]) => !s.complete && s.content.trim())
    .map(([k, s]) => ({ key: k, node: s.node, sectionId: s.sectionId, content: s.content }))
}
