import { useState } from 'react'
import { Modal, Form, Input, Button, message } from 'antd'
import { MailOutlined, KeyOutlined } from '@ant-design/icons'
import { useUserStore } from '@/stores/userStore'
import { api } from '@/services/api'

interface EmailBindModalProps {
  open: boolean
  onSuccess: () => void
}

export default function EmailBindModal({ open, onSuccess }: EmailBindModalProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const bindEmail = useUserStore((state) => state.bindEmail)

  const handleSubmit = async (values: { email: string; inviteCode: string }) => {
    setLoading(true)
    try {
      await api.register(values.email, values.inviteCode)
      bindEmail(values.email)
      message.success('注册成功')
      form.resetFields()
      onSuccess()
    } catch (error: any) {
      const msg = error?.response?.data?.message || error?.message || '注册失败，请检查邀请码是否正确'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="注册账号"
      open={open}
      footer={null}
      closable={false}
      maskClosable={false}
    >
      <div className="py-4">
        <p className="text-gray-600 mb-6">
          请输入邮箱和邀请码完成注册
        </p>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="your@email.com"
              size="large"
            />
          </Form.Item>
          <Form.Item
            name="inviteCode"
            label="邀请码"
            rules={[{ required: true, message: '请输入邀请码' }]}
          >
            <Input
              prefix={<KeyOutlined />}
              placeholder="请输入邀请码"
              size="large"
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loading}
            >
              确认注册
            </Button>
          </Form.Item>
        </Form>
      </div>
    </Modal>
  )
}
