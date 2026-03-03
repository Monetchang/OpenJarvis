import { create } from 'zustand'

interface ArticleStore {
  todayRefreshTrigger: number
  triggerTodayRefresh: () => void
}

export const useArticleStore = create<ArticleStore>((set) => ({
  todayRefreshTrigger: 0,
  triggerTodayRefresh: () =>
    set((state) => ({ todayRefreshTrigger: state.todayRefreshTrigger + 1 })),
}))
