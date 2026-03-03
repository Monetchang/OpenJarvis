import { create } from 'zustand'
import { RssFeed } from '@/types'

interface FeedStore {
  feeds: RssFeed[]
  setFeeds: (feeds: RssFeed[]) => void
  addFeed: (feed: RssFeed) => void
  updateFeed: (id: string, feed: Partial<RssFeed>) => void
  deleteFeed: (id: string) => void
}

export const useFeedStore = create<FeedStore>((set) => ({
  feeds: [],
  setFeeds: (feeds) => set({ feeds }),
  addFeed: (feed) => set((state) => ({ feeds: [...state.feeds, feed] })),
  updateFeed: (id, updatedFeed) =>
    set((state) => ({
      feeds: state.feeds.map((f) => (f.id === id ? { ...f, ...updatedFeed } : f)),
    })),
  deleteFeed: (id) => set((state) => ({ feeds: state.feeds.filter((f) => f.id !== id) })),
}))

