import { useState, useEffect, useCallback, useRef } from 'react'
import { Button, Card, message, Select } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { createWorkflow, getWorkflowEvents, getWorkflowWsUrl } from '@/services/workflowApi'
import type { Idea } from '@/types'
import HeaderBar from './HeaderBar'
import Timeline from './Timeline'
import Composer from './Composer'
import OutlineConfirmPanel from './OutlineConfirmPanel'
import { deriveUIState } from './utils/eventDisplay'
import type { WorkflowEvent, WsStatus, ArtifactMeta } from './types'

const MAX_WS_RECONNECT_ATTEMPTS = 5
const STORAGE_KEY_IDEA = 'create_chat_idea'

const STYLE_OPTIONS = ['专业报告', '博客随笔', '营销文案', '技术教程', '新闻资讯']
const AUDIENCE_OPTIONS = ['技术从业者', '普通消费者', '学生群体', '企业管理者', '创业者']

function persistIdea(idea: Idea) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY_IDEA,
      JSON.stringify({
        id: idea.id,
        title: idea.title,
        relatedArticles: idea.relatedArticles,
      })
    )
  } catch {
    // ignore
  }
}

function loadIdeaFromStorage(): Pick<Idea, 'id' | 'title' | 'relatedArticles'> | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_IDEA)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (o && typeof o.id === 'string' && typeof o.title === 'string' && Array.isArray(o.relatedArticles))
      return { id: o.id, title: o.title, relatedArticles: o.relatedArticles }
  } catch {
    // ignore
  }
  return null
}

function findLatestWaitingUserConfirmOutline(events: WorkflowEvent[]): WorkflowEvent | null {
  const candidates = events.filter(
    (e) => e.type === 'stage.waiting_user' && (e.payload?.action_required as string) === 'confirm_outline'
  )
  if (candidates.length === 0) return null
  return candidates.reduce((a, b) => (a.seq > b.seq ? a : b))
}

function isWaitingUserResolved(events: WorkflowEvent[], waitingSeq: number): boolean {
  return events.some(
    (e) =>
      e.seq > waitingSeq &&
      (e.type === 'user_action.applied' ||
        e.type === 'graph.resumed' ||
        (e.type === 'stage.started' && e.seq > waitingSeq) ||
        (e.type === 'graph.started' && e.seq > waitingSeq))
  )
}

function buildArtifactMetaFromPayload(p: Record<string, unknown>): ArtifactMeta | null {
  const id = (p.artifact_id as string)
  if (!id) return null
  return {
    artifact_id: id,
    type: (p.type as string) ?? '',
    version: (p.version as number) ?? 0,
    title: (p.title as string) ?? undefined,
    content_preview: (p.content_preview as string) ?? undefined,
    scope_key: (p.scope_key as string) ?? undefined,
    created_by: (p.created_by as string) ?? undefined,
  }
}

function mergeEventsBySeq(
  prev: WorkflowEvent[],
  seenSeq: Set<number>,
  newEvents: WorkflowEvent[]
): { events: WorkflowEvent[]; lastSeq: number; added: WorkflowEvent[] } {
  let lastSeq = prev.length ? Math.max(...prev.map((e) => e.seq)) : 0
  const prevSeqs = new Set(prev.map((e) => e.seq))
  const list = [...prev]
  const added: WorkflowEvent[] = []
  for (const e of newEvents) {
    const isInList = prevSeqs.has(e.seq)
    if (seenSeq.has(e.seq) && isInList) continue
    if (!seenSeq.has(e.seq)) seenSeq.add(e.seq)
    if (!isInList) {
      list.push(e)
      added.push(e)
    }
    if (e.seq > lastSeq) lastSeq = e.seq
  }
  list.sort((a, b) => a.seq - b.seq)
  return { events: list, lastSeq, added }
}

export default function Chat() {
  const navigate = useNavigate()
  const location = useLocation()
  const [idea, setIdea] = useState<Idea | (Pick<Idea, 'id' | 'title' | 'relatedArticles'> & { reason?: string }) | null>(() => {
    const fromState = (location.state as { idea?: Idea })?.idea
    if (fromState) {
      persistIdea(fromState)
      return fromState
    }
    return loadIdeaFromStorage()
  })
  useEffect(() => {
    const fromState = (location.state as { idea?: Idea })?.idea
    if (fromState) {
      persistIdea(fromState)
      setIdea(fromState)
    }
  }, [location.state])

  const [phase, setPhase] = useState<'config' | 'running'>('config')
  const [style, setStyle] = useState(STYLE_OPTIONS[0])
  const [audience, setAudience] = useState(AUDIENCE_OPTIONS[0])
  const startedRef = useRef(false)

  const [workflowId, setWorkflowId] = useState<string | null>(null)
  const [events, setEvents] = useState<WorkflowEvent[]>([])
  const [lastSeq, setLastSeq] = useState(0)
  const lastSeqRef = useRef(0)
  lastSeqRef.current = lastSeq
  const seenSeqRef = useRef<Set<number>>(new Set())
  const llmThinkingSeqRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirmOutlineLoading, setConfirmOutlineLoading] = useState(false)
  const [submittedForWaitingSeq, setSubmittedForWaitingSeq] = useState<number | null>(null)
  const [confirmedOutlineSections, setConfirmedOutlineSections] = useState<{ id: string; title: string }[] | null>(null)
  const [artifactIndex, setArtifactIndex] = useState<Map<string, ArtifactMeta>>(new Map())

  const initWorkflow = useCallback(async () => {
    setLoading(true)
    setError(null)
    setSubmittedForWaitingSeq(null)
    try {
      const { workflow_id } = await createWorkflow()
      setWorkflowId(workflow_id)
      const { events: evs, last_seq: _lastSeq } = await getWorkflowEvents(workflow_id, 0)
      const { events: merged, lastSeq: nextSeq } = mergeEventsBySeq([], seenSeqRef.current, evs)
      setEvents(merged)
      setLastSeq(nextSeq)
      lastSeqRef.current = nextSeq
      const index = new Map<string, ArtifactMeta>()
      for (const e of merged) {
        if (e.type === 'artifact.created' && e.payload) {
          const meta = buildArtifactMetaFromPayload(e.payload)
          if (meta) index.set(meta.artifact_id, meta)
        }
      }
      setArtifactIndex(index)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求失败（front）'
      setError(msg)
      message.error('后端不可用或创建 workflow 失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    initWorkflow()
  }, [initWorkflow])

  useEffect(() => {
    if (!workflowId) return
    const url = getWorkflowWsUrl(workflowId)
    setWsStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => {
      reconnectAttemptRef.current = 0
      setWsStatus('connected')
    }
    ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data as string)
        const items = Array.isArray(parsed) ? parsed : [parsed]
        const eventsToAdd: WorkflowEvent[] = []
        for (let data of items) {
          if (data && typeof data === 'object') {
            if (data.event && typeof data.event === 'object') data = data.event
            else if (data.data && typeof data.data === 'object') data = data.data
          }
          if (!data || typeof data !== 'object') continue
          const d = data as Record<string, unknown>
          const type = String(d.type ?? '')
          if (!type) continue
          let seq: number
          if (type === 'llm.thinking' && (typeof d.seq !== 'number' && typeof d.seq !== 'string')) {
            seq = -1e9 + llmThinkingSeqRef.current++
          } else {
            seq = typeof d.seq === 'number' ? d.seq : typeof d.seq === 'string' ? parseInt(d.seq, 10) : NaN
            if (Number.isNaN(seq)) continue
          }
          if (type.startsWith('ws.')) continue
          eventsToAdd.push({
            ...d,
            seq,
            type: String(type),
            payload: (d.payload as Record<string, unknown>) ?? {},
            workflow_id: String(d.workflow_id ?? ''),
            created_at: String(d.created_at ?? new Date().toISOString()),
          } as WorkflowEvent)
        }
        if (eventsToAdd.length === 0) return
        setArtifactIndex((prev) => {
          const next = new Map(prev)
          for (const e of eventsToAdd) {
            if (e.type === 'artifact.created' && e.payload) {
              const meta = buildArtifactMetaFromPayload(e.payload)
              if (meta) next.set(meta.artifact_id, meta)
            }
          }
          return next
        })
        for (const e of eventsToAdd) {
          if (e.type === 'action.ack') {
            const status = (e.payload?.status as string) ?? ''
            if (status === 'REJECTED' || status === 'FAILED') {
              const reason = (e.payload?.reason as string) ?? '操作失败'
              message.error(reason)
            }
          }
        }
        setEvents((prev) => {
          const withoutOptimistic = prev.filter((e) => !e._optimistic)
          const hasServerUserReply = eventsToAdd.some(
            (e) => e.type === 'chat.message' && (e.payload?.role as string) === 'user'
          )
          const base = hasServerUserReply ? withoutOptimistic : prev
          const { events: next, lastSeq: nextSeq } = mergeEventsBySeq(base, seenSeqRef.current, eventsToAdd)
          setLastSeq(nextSeq)
          return next
        })
      } catch {
        // ignore parse error
      }
    }
    ws.onclose = () => scheduleReconnect()
    ws.onerror = () => scheduleReconnect()
    const scheduleReconnect = () => {
      if (reconnectAttemptRef.current >= MAX_WS_RECONNECT_ATTEMPTS) {
        setWsStatus('disconnected')
        message.warning('WebSocket 连接失败，已达最大重试次数，请点击重连')
        return
      }
      setWsStatus('reconnecting')
      const currentLastSeq = lastSeqRef.current
      getWorkflowEvents(workflowId, currentLastSeq)
        .then(({ events: evs, last_seq: _lastSeq }) => {
          setEvents((prev) => {
            const { events: merged, lastSeq: nextSeq } = mergeEventsBySeq(
              prev,
              seenSeqRef.current,
              evs
            )
            setLastSeq(nextSeq)
            lastSeqRef.current = nextSeq
            setArtifactIndex((idx) => {
              const next = new Map(idx)
              for (const e of evs) {
                if (e.type === 'artifact.created' && e.payload) {
                  const meta = buildArtifactMetaFromPayload(e.payload)
                  if (meta) next.set(meta.artifact_id, meta)
                }
              }
              return next
            })
            return merged
          })
        })
        .catch(() => {})
        .finally(() => {
          const attempt = reconnectAttemptRef.current
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
          reconnectAttemptRef.current += 1
          reconnectTimeoutRef.current = setTimeout(
            () => setReconnectAttempt((prev) => prev + 1),
            delay
          )
        })
    }
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      wsRef.current = null
      ws.close()
      setWsStatus('disconnected')
    }
  }, [workflowId, reconnectAttempt])

  const sendMessage = useCallback((text: string) => {
    if (!workflowId) return
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const payload = { type: 'chat.send', payload: { text, client_msg_id: id, idempotency_key: id } }
    ws.send(JSON.stringify(payload))
    const optimisticSeq = lastSeqRef.current + 1 + 1000000
    const optimistic: WorkflowEvent = {
      workflow_id: workflowId ?? '',
      seq: optimisticSeq,
      type: 'chat.message',
      payload: { role: 'user', text },
      created_at: new Date().toISOString(),
      _optimistic: true,
    }
    setEvents((prev) => [...prev, optimistic])
  }, [workflowId])

  const handleNewWorkflow = () => {
    seenSeqRef.current.clear()
    reconnectAttemptRef.current = 0
    setEvents([])
    setLastSeq(0)
    setArtifactIndex(new Map())
    initWorkflow()
  }

  const handleReconnect = () => {
    reconnectAttemptRef.current = 0
    setReconnectAttempt((prev) => prev + 1)
  }

  const handleConfirmOutline = useCallback(
    (
      outline: { sections?: { id: string; title: string }[]; _artifact_id?: string },
      outlineArtifactId: string | undefined,
      waitingSeq: number
    ) => {
      const ws = wsRef.current
      if (!ws || ws.readyState !== WebSocket.OPEN) return
      setConfirmOutlineLoading(true)
      const idempotencyKey =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`
      const clientActionId =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`
      const msg = {
        type: 'action.dispatch',
        payload: {
          action: 'outline.confirm',
          input: {
            outline_confirmed: true,
            outline,
            outline_artifact_id: outlineArtifactId ?? outline._artifact_id,
          },
        },
        meta: {
          idempotency_key: idempotencyKey,
          client_action_id: clientActionId,
          client_ts_ms: Date.now(),
          source: 'web',
          schema_version: 1,
        },
      }
      const raw = JSON.stringify(msg)
      ws.send(raw)
      setSubmittedForWaitingSeq(waitingSeq)
      setConfirmedOutlineSections(outline.sections ?? [])
      setConfirmOutlineLoading(false)
    },
    []
  )

  const handleStartGenerate = useCallback(() => {
    if (!idea || startedRef.current) return
    const ws = wsRef.current
    if (!ws) {
      message.warning('WebSocket 未就绪')
      return
    }
    if (ws.readyState !== WebSocket.OPEN) {
      message.warning('连接未就绪，请稍候')
      return
    }
    const refs = idea.relatedArticles?.map((a) => a.url) ?? []
    const idempotencyKey =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const clientActionId =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const dispatchMsg = {
      type: 'action.dispatch',
      payload: {
        action: 'workflow.start',
        input: {
          title: idea.title,
          refs,
          style,
          audience,
          language: 'zh-CN',
          length: 'medium',
          idea_id: idea.id,
        },
      },
      meta: {
        idempotency_key: idempotencyKey,
        client_action_id: clientActionId,
        client_ts_ms: Date.now(),
        source: 'web',
        schema_version: 1,
      },
    }
    ws.send(JSON.stringify(dispatchMsg))
    startedRef.current = true
    setPhase('running')
  }, [idea, style, audience])

  if (loading && !workflowId) {
    return (
      <div className="flex items-center justify-center py-8">
        <span className="text-gray-500">加载中…</span>
      </div>
    )
  }

  if (!idea) {
    return (
      <div className="flex flex-col h-[calc(100vh-8rem)]">
        <div className="flex items-center gap-2 mb-2">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <h1 className="text-xl font-medium m-0">创作工作台</h1>
        </div>
        <Card className="mb-4">
          <p className="text-gray-600 mb-2">缺少选题信息，请从创作入口进入</p>
          <Button type="primary" onClick={() => navigate('/writing-assistant')}>
            返回创作入口
          </Button>
        </Card>
      </div>
    )
  }

  const waitingUserEvent = findLatestWaitingUserConfirmOutline(events)
  const waitingUserResolved = waitingUserEvent ? isWaitingUserResolved(events, waitingUserEvent.seq) : true
  const userSubmittedForThisWaiting = waitingUserEvent && submittedForWaitingSeq === waitingUserEvent.seq
  const showOutlineConfirm = waitingUserEvent && !waitingUserResolved && !userSubmittedForThisWaiting
  const composerDisabled = phase === 'config' || wsStatus !== 'connected' || !!showOutlineConfirm

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 mb-2">
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
        <h1 className="text-xl font-medium m-0">创作工作台</h1>
      </div>
      {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
      <HeaderBar
        workflowId={workflowId ?? ''}
        wsStatus={wsStatus}
        onNewWorkflow={handleNewWorkflow}
        onReconnect={handleReconnect}
      />
      {phase === 'config' ? (
        <Card title="配置" className="mb-4">
          <div className="mb-3">
            <div className="text-sm text-gray-500 mb-1">选题</div>
            <div className="font-medium">{idea.title}</div>
          </div>
          <div className="mb-3">
            <div className="text-sm text-gray-500 mb-1">参考文章</div>
            <ul className="list-none pl-0 text-sm space-y-1">
              {(idea.relatedArticles ?? []).map((a, i) => (
                <li key={i}>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {a.title}
                  </a>
                  <span className="text-gray-500 ml-1">({a.source})</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap gap-4 mb-3">
            <div>
              <span className="text-sm text-gray-500 mr-2">写作风格</span>
              <Select
                value={style}
                onChange={setStyle}
                options={STYLE_OPTIONS.map((s) => ({ label: s, value: s }))}
                style={{ width: 140 }}
              />
            </div>
            <div>
              <span className="text-sm text-gray-500 mr-2">目标人群</span>
              <Select
                value={audience}
                onChange={setAudience}
                options={AUDIENCE_OPTIONS.map((a) => ({ label: a, value: a }))}
                style={{ width: 140 }}
              />
            </div>
          </div>
          <Button
            type="primary"
            onClick={handleStartGenerate}
            disabled={wsStatus !== 'connected'}
          >
            {wsStatus !== 'connected' ? '连接未就绪' : '开始生成'}
          </Button>
        </Card>
      ) : (
        <>
          <Card size="small" className="mb-2">
            <div className="text-sm">
              <span className="text-gray-500">文章标题：</span>
              <span className="font-medium">{idea?.title ?? '—'}</span>
            </div>
            <div className="text-sm mt-1">
              <span className="text-gray-500">已选：</span>
              <span>{style}</span>
              <span className="text-gray-400 mx-1">/</span>
              <span>{audience}</span>
            </div>
          </Card>
          {(() => {
            const uiState = deriveUIState(events)
            if (uiState === 'WAITING_USER') return null
            if (uiState === 'COMPLETED' || uiState === 'ERROR') return null
            return <div className="text-sm text-blue-600 mb-2">正在生成…</div>
          })()}
        </>
      )}
      {showOutlineConfirm && waitingUserEvent && (() => {
        const data = (waitingUserEvent.payload?.payload as Record<string, unknown>) ?? waitingUserEvent.payload ?? {}
        const outline = (data.outline as { sections?: { id: string; title: string }[]; _artifact_id?: string }) ?? {}
        const outlineArtifactId = (data.outline_artifact_id as string) ?? outline?._artifact_id
        return (
          <OutlineConfirmPanel
            outline={outline}
            outlineArtifactId={outlineArtifactId}
            onConfirm={(o, id) => handleConfirmOutline(o, id, waitingUserEvent.seq)}
            loading={confirmOutlineLoading}
          />
        )
      })()}
      {userSubmittedForThisWaiting && !waitingUserResolved && confirmedOutlineSections && (
        <Card size="small" title="已确认大纲" className="mb-2">
          <ul className="list-none pl-0 text-sm space-y-1 mb-1">
            {confirmedOutlineSections.map((s, i) => (
              <li key={s.id ?? i}>
                <span className="text-gray-500">{i + 1}.</span> {s.title}
              </li>
            ))}
          </ul>
          <span className="text-gray-400 text-xs">正在按此大纲生成正文…</span>
        </Card>
      )}
      <Timeline
        events={events}
        workflowId={workflowId ?? ''}
        artifactIndex={artifactIndex}
        articleTitle={idea?.title ?? undefined}
      />
      <Composer onSend={sendMessage} disabled={composerDisabled} />
    </div>
  )
}
