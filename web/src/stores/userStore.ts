import { create } from 'zustand'
import { User } from '@/types'

interface UserStore {
  user: User
  setUser: (user: User) => void
  bindEmail: (email: string) => void
  logout: () => void
  checkEmailBound: () => boolean
}

const STORAGE_KEY = 'ucreativity_user'

const loadUserFromStorage = (): User => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return JSON.parse(stored)
  }
  return { email: null, isEmailBound: false }
}

const saveUserToStorage = (user: User) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
}

const defaultUser: User = { email: null, isEmailBound: false }

export const useUserStore = create<UserStore>((set, get) => ({
  user: loadUserFromStorage(),
  setUser: (user: User) => {
    saveUserToStorage(user)
    set({ user })
  },
  bindEmail: (email: string) => {
    const user = { email, isEmailBound: true }
    saveUserToStorage(user)
    set({ user })
  },
  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ user: defaultUser })
  },
  checkEmailBound: () => {
    return get().user.isEmailBound
  },
}))

