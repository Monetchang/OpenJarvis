import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import WritingAssistant from '@/pages/WritingAssistant'
import Feeds from '@/pages/Feeds'
import Settings from '@/pages/Settings'
import Chat from '@/pages/create/Chat'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/writing-assistant" replace />} />
          <Route path="writing-assistant" element={<WritingAssistant />} />
          <Route path="feeds" element={<Feeds />} />
          <Route path="create/chat" element={<Chat />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
