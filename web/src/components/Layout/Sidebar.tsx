import { Layout, Menu } from 'antd'
import { EditOutlined, SettingOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Sider } = Layout

interface SidebarProps {
  collapsed: boolean
  onCollapse: (collapsed: boolean) => void
}

export default function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/writing-assistant',
      icon: <EditOutlined />,
      label: '写作助手',
    },
    {
      key: '/feeds',
      icon: <UnorderedListOutlined />,
      label: '订阅源管理',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      className="bg-white"
      width={200}
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        className="h-full border-r-0"
      />
    </Sider>
  )
}

