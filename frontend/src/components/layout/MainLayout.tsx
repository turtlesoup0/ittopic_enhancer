import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  CheckCircle,
  Lightbulb,
  Menu,
  X
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/lib/store'

const navigation = [
  { name: '대시보드', href: '/', icon: LayoutDashboard },
  { name: '토픽 관리', href: '/topics', icon: FileText },
  { name: '검증', href: '/validation', icon: CheckCircle },
  { name: '제안', href: '/proposals', icon: Lightbulb },
]

export function MainLayout() {
  const location = useLocation()
  const { sidebarOpen, toggleSidebar } = useAppStore()

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center px-4">
          <Button
            variant="ghost"
            size="icon"
            className="mr-2 lg:hidden"
            onClick={toggleSidebar}
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <div className="flex-1">
            <h1 className="text-lg font-semibold">ITPE Topic Enhancement</h1>
          </div>
        </div>
      </header>

      <div className="container flex-1 items-start md:grid md:grid-cols-[220px_1fr] md:gap-6 lg:grid-cols-[240px_1fr] lg:gap-10">
        {/* Sidebar */}
        <aside
          className={cn(
            'fixed top-14 z-30 -ml-2 h-[calc(100vh-3.5rem)] w-full shrink-0 overflow-y-auto border-r bg-background transition-transform duration-200 md:sticky md:block',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          )}
        >
          <nav className="grid items-start px-2 py-4 text-sm font-medium">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 transition-all hover:text-primary',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground'
                  )}
                  onClick={() => {
                    // Close sidebar on mobile after navigation
                    if (window.innerWidth < 1024) {
                      toggleSidebar()
                    }
                  }}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex w-full flex-col gap-4 py-4 md:py-8">
          <Outlet />
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-14 md:flex-row">
          <p className="text-sm text-muted-foreground">
            © 2025 ITPE Topic Enhancement System. All rights reserved.
          </p>
          <p className="text-sm text-muted-foreground">
            Powered by FastAPI + React
          </p>
        </div>
      </footer>
    </div>
  )
}
