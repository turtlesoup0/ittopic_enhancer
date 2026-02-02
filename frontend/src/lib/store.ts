import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  selectedDomain: string | null
  setSelectedDomain: (domain: string | null) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      selectedDomain: null,
      setSelectedDomain: (domain) => set({ selectedDomain: domain }),
    }),
    {
      name: 'app-storage',
    }
  )
)

interface ValidationState {
  taskId: string | null
  setTaskId: (taskId: string | null) => void
  results: any[]
  setResults: (results: any[]) => void
}

export const useValidationStore = create<ValidationState>()((set) => ({
  taskId: null,
  setTaskId: (taskId) => set({ taskId }),
  results: [],
  setResults: (results) => set({ results }),
}))
