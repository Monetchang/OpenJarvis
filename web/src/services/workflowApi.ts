import request from './request'
import type { WorkflowEvent, ArtifactMeta } from '@/pages/create/Chat/types'

export type ArtifactListResponse = {
  workflow_id: string
  artifacts: Array<{
    id: string
    type: string
    version: number
    scope_key?: string
    title?: string
    content_preview?: string
    content_json?: Record<string, unknown>
    created_by?: string
  }>
}

export function getWorkflowWsUrl(workflowId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:12135/api/v1'
  try {
    const u = new URL(base)
    const protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${u.host}/ws/workflows/${workflowId}`
  } catch {
    return `ws://localhost:12135/ws/workflows/${workflowId}`
  }
}

export async function createWorkflow(): Promise<{ workflow_id: string }> {
  const payload = {
    minimal: true,
    input_params: {},
  }

  const response = await request.post<
    { code?: number; data?: { workflow_id: string }; workflow_id?: string }
  >('/workflows', payload)

  const data = response?.data ?? response
  const workflowId =
    data?.workflow_id ??
    (response as unknown as { workflow_id: string })?.workflow_id

  if (!workflowId) throw new Error('无效的 workflow 响应')

  return { workflow_id: workflowId }
}

export async function getWorkflowEvents(
  workflowId: string,
  afterSeq: number,
  limit = 200
): Promise<{ events: WorkflowEvent[]; last_seq: number }> {
  const response = await request.get<{
    code?: number
    data?: { events: WorkflowEvent[]; last_seq: number }
    events?: WorkflowEvent[]
    last_seq?: number
  }>(`/workflows/${workflowId}/events`, { params: { after_seq: afterSeq, limit } })
  const data = response?.data ?? response
  const events = data?.events ?? (response as unknown as { events: WorkflowEvent[] })?.events ?? []
  const lastSeq = data?.last_seq ?? (response as unknown as { last_seq: number })?.last_seq ?? afterSeq
  return { events: Array.isArray(events) ? events : [], last_seq: lastSeq }
}

export async function listArtifacts(workflowId: string): Promise<ArtifactListResponse> {
  const response = await request.get<{ code?: number; data?: ArtifactListResponse } & ArtifactListResponse>(
    `/workflows/${workflowId}/artifacts`
  )
  const data = response?.data ?? response
  const artifacts = (data as ArtifactListResponse)?.artifacts ?? []
  return {
    workflow_id: workflowId,
    artifacts: Array.isArray(artifacts) ? artifacts : [],
  }
}

export async function getArtifact(workflowId: string, artifactId: string): Promise<ArtifactMeta | null> {
  const { artifacts } = await listArtifacts(workflowId)
  const a = artifacts.find((x) => x.id === artifactId)
  if (!a) return null
  return {
    artifact_id: a.id,
    type: a.type,
    version: a.version,
    title: a.title,
    content_preview: a.content_preview,
    scope_key: a.scope_key,
    created_by: a.created_by,
    content_json: a.content_json,
  }
}
