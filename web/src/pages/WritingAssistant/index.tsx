import { useState } from 'react'
import PushPreview from './components/PushPreview'
import IdeaGenerator from './components/IdeaGenerator'

export default function WritingAssistant() {
  const [activeTab, setActiveTab] = useState('today')
  return (
    <div className="space-y-6">
      <PushPreview onActiveTabChange={setActiveTab} />
      {activeTab !== 'history' && <IdeaGenerator />}
    </div>
  )
}

