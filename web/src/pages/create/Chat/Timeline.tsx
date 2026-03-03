import { useEffect, useRef } from 'react'
import type { WorkflowEvent, ArtifactMeta } from './types'
import { filterMainTimelineEvents, getSystemDetailEvents, getDisplayConfig, deriveThinkingStreams } from './utils/eventDisplay'
import ChatBubble from './ChatBubble'
import EventCard from './EventCard'
import SummaryCard from './SummaryCard'
import StageStatusCard from './StageStatusCard'
import InfoBanner from './InfoBanner'
import SuccessBanner from './SuccessBanner'
import ErrorCard from './ErrorCard'
import FinalArtifactCard from './FinalArtifactCard'
import OutlineArtifactCard from './OutlineArtifactCard'
import SectionDraftsGroupCard from './SectionDraftsGroupCard'
import ThinkingCard from './ThinkingCard'
import SystemDetails from './SystemDetails'

export interface TimelineProps {
  events: WorkflowEvent[]
  workflowId: string
  artifactIndex: Map<string, ArtifactMeta>
  articleTitle?: string
}

function eventKey(ev: WorkflowEvent): string {
  return ev._optimistic ? `opt-${ev.seq}` : `${ev.workflow_id}-${ev.seq}`
}

function getArtifactMetaFromEvent(ev: WorkflowEvent, index: Map<string, ArtifactMeta>): ArtifactMeta {
  const p = ev.payload ?? {}
  const id = (p.artifact_id as string) ?? ''
  const existing = id ? index.get(id) : undefined
  if (existing) return existing
  return {
    artifact_id: id,
    type: (p.type as string) ?? '',
    version: (p.version as number) ?? 0,
    title: (p.title as string) ?? undefined,
    content_preview: (p.content_preview as string) ?? undefined,
  }
}

export default function Timeline({ events, workflowId, artifactIndex, articleTitle }: TimelineProps) {
  const mainEvents = filterMainTimelineEvents(events)
  const systemEvents = getSystemDetailEvents(events)
  const thinkingStreams = deriveThinkingStreams(events)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [events.length])

  const sectionDraftEvents = mainEvents.filter(
    (e) => e.type === 'artifact.created' && (e.payload?.type as string) === 'section_draft'
  )
  const sectionDraftMetas = sectionDraftEvents
    .map((e) => {
      const meta = getArtifactMetaFromEvent(e, artifactIndex)
      return meta.artifact_id ? meta : null
    })
    .filter((m): m is ArtifactMeta => m != null)
  const mainWithoutSectionDrafts = mainEvents.filter(
    (e) => !(e.type === 'artifact.created' && (e.payload?.type as string) === 'section_draft')
  )

  const renderEvent = (ev: WorkflowEvent) => {
    const config = getDisplayConfig(ev.type, ev.payload ?? {})
    if (ev.type === 'chat.message') {
      return <ChatBubble key={eventKey(ev)} event={ev} />
    }
    if (config.component === 'StageStatusCard') return <StageStatusCard key={eventKey(ev)} event={ev} />
    if (config.component === 'InfoBanner') return <InfoBanner key={eventKey(ev)} event={ev} />
    if (config.component === 'SuccessBanner') return <SuccessBanner key={eventKey(ev)} event={ev} />
    if (config.component === 'ErrorCard') return <ErrorCard key={eventKey(ev)} event={ev} />
    if (config.component === 'FinalArtifactCard') {
      const meta = getArtifactMetaFromEvent(ev, artifactIndex)
      return <FinalArtifactCard key={eventKey(ev)} workflowId={workflowId} meta={meta} articleTitle={articleTitle} />
    }
    if (config.component === 'OutlineArtifactCard') {
      const meta = getArtifactMetaFromEvent(ev, artifactIndex)
      return <OutlineArtifactCard key={eventKey(ev)} workflowId={workflowId} meta={meta} />
    }
    if (config.component === 'OutlineConfirmPanel') {
      return <SummaryCard key={eventKey(ev)} event={ev} variant="highlight" />
    }
    return <EventCard key={eventKey(ev)} event={ev} />
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto py-2">
      {mainWithoutSectionDrafts.map(renderEvent)}
      {thinkingStreams.map((s) => (
        <ThinkingCard key={s.key} stream={s} />
      ))}
      {sectionDraftMetas.length > 0 && (
        <SectionDraftsGroupCard key="section-drafts-group" workflowId={workflowId} items={sectionDraftMetas} />
      )}
      {(systemEvents.length > 0 || events.length > 0) && (
        <SystemDetails events={systemEvents} allEvents={events} />
      )}
    </div>
  )
}
