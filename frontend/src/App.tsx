import { useState } from "react"
import {
  createBrowserRouter,
  RouterProvider,
  Outlet,
  NavLink,
  Navigate,
  Link,
} from "react-router-dom"
import {
  LayoutDashboardIcon,
  ServerIcon,
  GitForkIcon,
  MenuIcon,
  UploadIcon,
  FileTextIcon,
  BellIcon,
  BuildingIcon,
  ClipboardListIcon,
} from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { getNotifications } from "@/lib/api"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Toaster } from "@/components/ui/sonner"

import DashboardPage from "@/pages/DashboardPage"
import SystemsPage from "@/pages/SystemsPage"
import SystemDetailPage from "@/pages/SystemDetailPage"
import SystemFormPage from "@/pages/SystemFormPage"
import DependenciesPage from "@/pages/DependenciesPage"
import ImportPage from "@/pages/ImportPage"
import ReportsPage from "@/pages/ReportsPage"
import NotificationsPage from "@/pages/NotificationsPage"
import OrganizationsPage from "@/pages/OrganizationsPage"
import AuditPage from "@/pages/AuditPage"

// --- Notifikationsklocka ---

function NotificationBell() {
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => getNotifications(),
    refetchInterval: 60000, // Uppdatera varje minut
  })

  const count = data?.total ?? 0

  return (
    <Link
      to="/notifications"
      className="relative flex h-11 w-11 items-center justify-center rounded-md hover:bg-accent transition-colors"
      aria-label="Visa notifikationer"
    >
      <BellIcon className="size-5 text-muted-foreground hover:text-foreground transition-colors" />
      {count > 0 && (
        <span className="absolute top-1 right-1 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  )
}

// --- Navigationsstruktur ---

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
  { to: "/systems", label: "System", icon: ServerIcon },
  { to: "/organizations", label: "Organisationer", icon: BuildingIcon },
  { to: "/dependencies", label: "Beroendekarta", icon: GitForkIcon },
  { to: "/notifications", label: "Notifikationer", icon: BellIcon },
  { to: "/import", label: "Import", icon: UploadIcon },
  { to: "/reports", label: "Rapporter", icon: FileTextIcon },
  { to: "/audit", label: "Ändringslogg", icon: ClipboardListIcon },
]

// --- Sidofält (desktop) ---

function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 border-r bg-sidebar min-h-screen">
      <div className="px-4 py-4 border-b flex items-center justify-between">
        <span className="font-semibold text-sm tracking-tight">
          Systemregister
        </span>
        <NotificationBell />
      </div>
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              ].join(" ")
            }
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

// --- Mobil-meny ---

function MobileNav({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-56 p-0">
        <SheetHeader className="px-4 py-4 border-b">
          <SheetTitle className="text-sm font-semibold tracking-tight">
            Systemregister
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-1 p-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => onOpenChange(false)}
              className={({ isActive }) =>
                [
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-foreground hover:bg-accent hover:text-accent-foreground",
                ].join(" ")
              }
            >
              <Icon className="size-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}

// --- Layout ---

function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <MobileNav open={mobileOpen} onOpenChange={setMobileOpen} />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Mobil-header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b">
          <Button variant="ghost" size="icon-sm" onClick={() => setMobileOpen(true)}>
            <MenuIcon className="size-5" />
            <span className="sr-only">Öppna meny</span>
          </Button>
          <span className="font-semibold text-sm">Systemregister</span>
          <NotificationBell />
        </header>

        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  )
}

// --- Router (data router krävs för useBlocker) ---

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/systems", element: <SystemsPage /> },
      { path: "/systems/new", element: <SystemFormPage /> },
      { path: "/systems/:id", element: <SystemDetailPage /> },
      { path: "/systems/:id/edit", element: <SystemFormPage /> },
      { path: "/organizations", element: <OrganizationsPage /> },
      { path: "/dependencies", element: <DependenciesPage /> },
      { path: "/notifications", element: <NotificationsPage /> },
      { path: "/import", element: <ImportPage /> },
      { path: "/reports", element: <ReportsPage /> },
      { path: "/audit", element: <AuditPage /> },
    ],
  },
])

// --- App ---

export default function App() {
  return <RouterProvider router={router} />
}
