import FeedManager from './components/FeedManager'
import PushPreview from './components/PushPreview'
import IdeaGenerator from './components/IdeaGenerator'

export default function WritingAssistant() {
  return (
    <div className="space-y-6">
      <FeedManager />
      <PushPreview />
      <IdeaGenerator />
    </div>
  )
}

