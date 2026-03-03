import { Layout, Space, Badge, Avatar, Tag, Dropdown } from 'antd'
import type { MenuProps } from 'antd'
import { BellOutlined, CheckCircleOutlined, LogoutOutlined } from '@ant-design/icons'
import { useUserStore } from '@/stores/userStore'
import { api } from '@/services/api'

const { Header: AntHeader } = Layout

export default function Header() {
  const { user, logout: logoutStore } = useUserStore()

  const onLogout = () => {
    api.logout().finally(() => {
      logoutStore()
    })
  }

  const items: MenuProps['items'] = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: onLogout },
  ]

  return (
    <AntHeader className="bg-white shadow-sm flex items-center justify-between px-6">
      <div className="flex items-center space-x-2">
        <div className="text-xl font-bold text-blue-600">UCreativity</div>
        <div className="text-sm text-gray-500">智能写作工作台</div>
      </div>
      <Space size="large">
        {user.isEmailBound ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            {user.email}
          </Tag>
        ) : (
          <Tag color="warning">未绑定邮箱</Tag>
        )}
        <Badge count={0} showZero={false}>
          <BellOutlined className="text-xl cursor-pointer hover:text-blue-600" />
        </Badge>
        <Dropdown menu={{ items }} trigger={['click']}>
          <Avatar className="bg-blue-500 cursor-pointer">
            {user.email ? user.email[0].toUpperCase() : 'U'}
          </Avatar>
        </Dropdown>
      </Space>
    </AntHeader>
  )
}

