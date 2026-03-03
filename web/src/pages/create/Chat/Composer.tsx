import { useState } from 'react'
import { Button, Input } from 'antd'
import { SendOutlined } from '@ant-design/icons'

const { TextArea } = Input

interface ComposerProps {
  onSend?: (text: string) => void
  disabled?: boolean
}

export default function Composer({ onSend, disabled }: ComposerProps) {
  const [text, setText] = useState('')
  const handleSend = () => {
    const t = text.trim()
    if (!t || disabled) return
    onSend?.(t)
    setText('')
  }
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  return (
    <div className="flex gap-2 items-end border-t border-gray-200 pt-2">
      <TextArea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        autoSize={{ minRows: 2, maxRows: 4 }}
        className="flex-1"
      />
      <Button type="primary" icon={<SendOutlined />} onClick={handleSend} disabled={disabled}>
        发送
      </Button>
    </div>
  )
}
