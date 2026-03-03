import type { WorkflowEvent } from './Chat/types'

const EVENT_TYPE_LABELS: Record<string, string> = {
  'stage.waiting_user': '等待确认',
  'stage.started': '阶段开始',
  'stage.scheduled': '阶段调度',
  'stage.completed': '阶段完成',
  'graph.started': '流程开始',
  'graph.resumed': '继续生成',
  'graph.completed': '生成完成',
  'graph.failed': '流程失败',
  'workflow.configured': '已配置',
  'node.started': '节点开始',
  'node.completed': '节点完成',
  'node.failed': '节点失败',
  'artifact.created': '产物创建',
  'action.ack': '动作响应',
  'user_action.applied': '动作已应用',
  'llm.thinking': 'LLM 思考',
}

const NODE_NAME_LABELS: Record<string, string> = {
  fetch_and_extract_refs: '提取参考',
  synthesize_refs: '分析参考资料',
  plan_article: '规划写作蓝图',
  propose_outline: '拟定大纲',
  interrupt_for_outline_confirm: '等待确认大纲',
  write_sections: '撰写章节',
  finalize_markdown: '生成正文',
  assemble_article: '组装正文',
  quality_gate: '质量检查',
  node_a: '节点 A',
  node_b: '节点 B',
  node_c: '节点 C',
}

export function eventTypeLabel(type: string): string {
  return EVENT_TYPE_LABELS[type] ?? type
}

export function nodeNameLabel(node: string): string {
  return NODE_NAME_LABELS[node] ?? node
}

export function renderSummary(event: WorkflowEvent): string {
  const { type, payload } = event
  const p = payload ?? {}

  switch (type) {
    case 'stage.waiting_user':
      return (p.action_required as string) === 'confirm_outline' ? '等待确认大纲' : '等待用户操作'
    case 'stage.started':
      return (p.attempt as number) > 1 ? `继续生成（第 ${p.attempt} 次）` : '开始生成'
    case 'workflow.configured':
      return [p.style, p.audience].filter(Boolean).length
        ? `已配置：${[p.style, p.audience].filter(Boolean).join(' / ')}`
        : '已配置'
    case 'graph.resumed':
      return '已继续生成…'
    case 'graph.completed':
      return '生成完成'
    case 'graph.started':
      return '流程开始'
    case 'node.started': {
      const node = (p.node_id ?? p.node) as string
      return `开始：${nodeNameLabel(node ?? '')}`
    }
    case 'node.completed': {
      const node = (p.node_id ?? p.node) as string
      return `完成：${nodeNameLabel(node ?? '')}`
    }
    case 'action.ack': {
      const status = (p.status as string) ?? ''
      const action = (p.action as string) ?? ''
      if (status === 'REJECTED' || status === 'FAILED') return `操作失败：${(p.reason as string) ?? ''}`
      if (status === 'ACCEPTED') return `已受理：${action}`
      if (status === 'DUPLICATE') return `重复：${action}`
      return `动作响应：${action}`
    }
    case 'user_action.applied':
      return '动作已应用'
    case 'llm.thinking': {
      const node = (p.node as string) ?? ''
      const sectionId = (p.section_id as string) ?? ''
      const label = nodeNameLabel(node)
      return sectionId ? `${label} · ${sectionId}` : label
    }
    case 'artifact.created': {
      const artType = (p.type as string) ?? ''
      if (artType === 'final_markdown') return `最终正文 (v${p.version ?? ''})`
      if (artType === 'outline_plan') return `大纲 (v${p.version ?? ''})`
      if (artType === 'article_plan') return `写作蓝图 (v${p.version ?? ''})`
      if (artType === 'section_draft') return `章节草稿`
      return `产物：${artType}`
    }
    default:
      return EVENT_TYPE_LABELS[type] ? eventTypeLabel(type) : `系统事件：${type}`
  }
}
