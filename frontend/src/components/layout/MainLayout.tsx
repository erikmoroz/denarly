import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import Sidebar from './Sidebar'

const SIDEBAR_COLLAPSED_KEY = 'monie-sidebar-collapsed'

interface MainLayoutProps {
  children: ReactNode
}

export default function MainLayout({ children }: MainLayoutProps) {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)')

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
      <div className="min-h-screen bg-surface">
        {/* Mobile top bar */}
        <div className="fixed top-0 left-0 right-0 z-30 bg-[rgba(250,249,248,0.80)] backdrop-blur-md flex items-center gap-3 px-4 py-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-primary hover:bg-white/50 transition-colors flex items-center justify-center"
            aria-label="Open navigation menu"
          >
            <span className="material-symbols-outlined text-2xl select-none">menu</span>
          </button>
          <span className="font-headline font-black text-primary text-xl tracking-tight">Monie</span>
        </div>

        {/* Mobile drawer overlay */}
        {mobileOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-[rgba(47,51,51,0.5)] transition-opacity"
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
        <main className="pt-16 px-4 py-6">
          {children}
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-surface">
      <div className="flex-shrink-0">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={toggleCollapse}
        />
      </div>
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  )
}
