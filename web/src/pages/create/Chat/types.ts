export type WorkflowEvent = {
  workflow_id: string
  seq: number
  type: string
  payload: Record<string, unknown>
  created_at: string
  _optimistic?: boolean
}

export type WsStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

export type ArtifactMeta = {
  artifact_id: string
  type: string
  version: number
  title?: string
  content_preview?: string
  scope_key?: string
  created_by?: string
  content_json?: Record<string, unknown>
}

export type DisplayPriority = 'highlight' | 'normal' | 'collapse'

export type WorkflowUIState = 'WAITING_USER' | 'RUNNING' | 'COMPLETED' | 'ERROR' | 'IDLE'

export type EventDisplayConfig = {
  showInMain: boolean
  priority: DisplayPriority
  component: string
}
