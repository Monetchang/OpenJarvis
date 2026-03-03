import { Button, Space, Typography } from 'antd'
import type { WsStatus } from './types'

const { Text } = Typography

interface HeaderBarProps {
  workflowId: string
  wsStatus: WsStatus
  onNewWorkflow?: () => void
  onReconnect?: () => void
}

export default function HeaderBar({ workflowId, wsStatus, onNewWorkflow, onReconnect }: HeaderBarProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-200">
      <Space>
        <Text type="secondary">状态：</Text>
        <Text>{wsStatus}</Text>
        <Text type="secondary" className="ml-2">workflow_id：</Text>
        <Text copyable={!!workflowId}>{workflowId || '—'}</Text>
      </Space>
      <Space>
        {wsStatus === 'disconnected' && onReconnect && (
          <Button size="small" type="primary" onClick={onReconnect}>
            重连
          </Button>
        )}
        {onNewWorkflow && (
          <Button size="small" onClick={onNewWorkflow}>
            New Workflow
          </Button>
        )}
      </Space>
    </div>
  )
}
