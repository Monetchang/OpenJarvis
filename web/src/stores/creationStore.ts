import { create } from 'zustand'
import { Idea } from '@/types'

interface CreationStore {
  selectedIdea: Idea | null
  generatedContent: string
  isCreationAreaExpanded: boolean
  setSelectedIdea: (idea: Idea | null) => void
  setGeneratedContent: (content: string) => void
  expandCreationArea: () => void
  collapseCreationArea: () => void
}

export const useCreationStore = create<CreationStore>((set) => ({
  selectedIdea: null,
  generatedContent: '',
  isCreationAreaExpanded: false,
  setSelectedIdea: (idea) => set({ selectedIdea: idea }),
  setGeneratedContent: (content) => set({ generatedContent: content }),
  expandCreationArea: () => set({ isCreationAreaExpanded: true }),
  collapseCreationArea: () => set({ isCreationAreaExpanded: false }),
}))

