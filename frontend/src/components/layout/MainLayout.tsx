import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import Sidebar from './Sidebar'
import { HiMenu, HiPlus } from 'react-icons/hi'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import toast from 'react-hot-toast'

const SIDEBAR_COLLAPSED_KEY = 'monie-sidebar-collapsed'

interface MainLayoutProps {
  children: ReactNode
}

function NoWorkspaceMessage() {
  const { createWorkspace } = useWorkspace()
  const [isCreating, setIsCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')

  const handleCreate = async () => {
    if (!name.trim()) return
    setIsCreating(true)
    try {
      await createWorkspace(name.trim())
      toast.success('Workspace created')
      setShowForm(false)
      setName('')
    } catch {
      toast.error('Failed to create workspace')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">No workspace selected</h2>
        <p className="text-gray-500 mb-4">Create a workspace or ask to be added to one.</p>
        
        {!showForm ? (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
          >
            <HiPlus className="h-4 w-4" />
            Create Workspace
          </button>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Workspace name"
              className="block w-64 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={isCreating || !name.trim()}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
              <button
                onClick={() => { setShowForm(false); setName('') }}
                disabled={isCreating}
                className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MainLayout({ children }: MainLayoutProps) {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)')
  const { workspace, isLoading } = useWorkspace()

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
      return stored === 'true'
    }
    return false
  })

  const [mobileOpen, setMobileOpen] = useState(false)

  // Close mobile drawer on route change
  const location = useLocation()
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  // Close mobile drawer on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  // Auto-collapse on tablet
  useEffect(() => {
    if (isTablet) {
      setCollapsed(true)
    }
  }, [isTablet])

  const toggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next))
      return next
    })
  }

  if (isMobile) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Mobile top bar */}
        <div className="fixed top-0 left-0 right-0 z-30 bg-white border-b border-gray-200 flex items-center gap-3 px-4 py-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-1.5 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            aria-label="Open navigation menu"
          >
            <HiMenu className="h-6 w-6" />
          </button>
          <span className="text-lg font-bold text-gray-900">Monie</span>
        </div>

        {/* Mobile drawer overlay */}
        {mobileOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/40"
              onClick={() => setMobileOpen(false)}
            />
            <div className="fixed inset-y-0 left-0 z-50 flex">
              <Sidebar
                collapsed={false}
                onToggleCollapse={() => setMobileOpen(false)}
                onClose={() => setMobileOpen(false)}
              />
            </div>
          </>
        )}

        {/* Main content with top padding for the fixed bar */}
        <main className="pt-14 px-4 py-6">
          {!workspace && !isLoading ? <NoWorkspaceMessage /> : children}
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="flex-shrink-0">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={toggleCollapse}
        />
      </div>
      <main className="flex-1 overflow-y-auto p-6">
        {!workspace && !isLoading ? <NoWorkspaceMessage /> : children}
      </main>
    </div>
  )
}
