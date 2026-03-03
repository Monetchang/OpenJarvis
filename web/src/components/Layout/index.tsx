import { useState, useEffect } from 'react'
import { Layout as AntLayout } from 'antd'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import EmailBindModal from '@/components/EmailBindModal'
import { useUserStore } from '@/stores/userStore'
import { api } from '@/services/api'

const { Content } = AntLayout

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, setUser } = useUserStore()
  const isEmailBound = user.isEmailBound
  const showEmailModal = !isEmailBound

  useEffect(() => {
    api.getCurrentUser().then((data) => {
      if (data?.isEmailBound && data?.email) {
        setUser({ email: data.email, isEmailBound: true })
      }
    }).catch(() => { /* 未登录或未绑定，保持本地状态 */ })
  }, [setUser])

  return (
    <AntLayout className="min-h-screen">
      <Header />
      <AntLayout>
        <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />
        <Content className="p-6 bg-gray-50">
          <Outlet />
        </Content>
      </AntLayout>
      <EmailBindModal open={showEmailModal} onSuccess={() => {}} />
    </AntLayout>
  )
}

