import { useState, useEffect } from "react"
import {
  createBrowserRouter,
  RouterProvider,
  Outlet,
  NavLink,
  Navigate,
  Link,
  useLocation,
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
  SunIcon,
  MoonIcon,
  FolderIcon,
  PuzzleIcon,
  PackageIcon,
  DatabaseIcon,
  CheckSquareIcon,
} from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { getNotifications } from "@/lib/api"
import { useKeyboardShortcuts } from "@/lib/useKeyboardShortcuts"

import { SkipLink } from "@/components/SkipLink"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { KeyboardHelpModal } from "@/components/shared/KeyboardHelpModal"
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
import ObjektPage from "@/pages/ObjektPage"
import ComponentsPage from "@/pages/ComponentsPage"
import ModulesPage from "@/pages/ModulesPage"
import InformationAssetsPage from "@/pages/InformationAssetsPage"
import ApprovalsPage from "@/pages/ApprovalsPage"

// --- Dark mode ---

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false
    const stored = localStorage.getItem("theme")
    if (stored === "dark") return true
    if (stored === "light") return false
    return window.matchMedia("(prefers-color-scheme: dark)").matches
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add("dark")
      localStorage.setItem("theme", "dark")
    } else {
      root.classList.remove("dark")
      localStorage.setItem("theme", "light")
    }
  }, [dark])

  return [dark, setDark] as const
}

// --- Dynamic page title ---

const ROUTE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/systems": "System",
  "/systems/new": "Nytt system",
  "/organizations": "Organisationer",
  "/dependencies": "Beroendekarta",
  "/notifications": "Notifikationer",
  "/import": "Import",
  "/reports": "Rapporter",
  "/audit": "Ändringslogg",
  "/objekt": "Objekt",
  "/components": "Komponenter",
  "/modules": "Moduler",
  "/information-assets": "Informationsmängder",
  "/approvals": "Godkännanden",
}

function usePageTitle() {
  const location = useLocation()
  useEffect(() => {
    const path = location.pathname
    // Check exact match first, then prefix
    const title =
      ROUTE_TITLES[path] ??
      (path.startsWith("/systems/") && path.endsWith("/edit")
        ? "Redigera system"
        : path.startsWith("/systems/")
          ? "Systemdetalj"
          : "Systemregister")
    document.title = `${title} | Systemregister`
  }, [location.pathname])
}

// --- Notifikationsklocka ---

function NotificationBell() {
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => getNotifications(),
    refetchInterval: 60000,
  })

  const count = data?.total ?? 0

  return (
    <Link
      to="/notifications"
      className="relative flex h-9 w-9 items-center justify-center rounded-lg hover:bg-accent transition-colors duration-150"
      aria-label="Visa notifikationer"
    >
      <BellIcon className="size-[18px] text-muted-foreground" />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white">
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
  { to: "/objekt", label: "Objekt", icon: FolderIcon },
  { to: "/components", label: "Komponenter", icon: PuzzleIcon },
  { to: "/modules", label: "Moduler", icon: PackageIcon },
  { to: "/information-assets", label: "Informationsmängder", icon: DatabaseIcon },
  { to: "/approvals", label: "Godkännanden", icon: CheckSquareIcon },
  { to: "/audit", label: "Ändringslogg", icon: ClipboardListIcon },
]

// --- Sidofält (desktop) ---

function Sidebar({ dark, onToggleDark }: { dark: boolean; onToggleDark: () => void }) {
  return (
    <aside className="hidden md:flex flex-col w-60 shrink-0 border-r border-sidebar-border bg-sidebar min-h-screen">
      {/* Header */}
      <div className="px-5 py-5 border-b border-sidebar-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
            S
          </div>
          <span className="font-semibold text-sm tracking-tight text-sidebar-foreground">
            Systemregister
          </span>
        </div>
        <NotificationBell />
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-0.5 px-3 py-3 flex-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-sm"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              ].join(" ")
            }
          >
            <Icon className="size-[18px] shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer with dark mode toggle */}
      <div className="px-3 py-3 border-t border-sidebar-border">
        <button
          onClick={onToggleDark}
          className="flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground transition-all duration-150"
          aria-label={dark ? "Byt till ljust tema" : "Byt till mörkt tema"}
        >
          {dark ? <SunIcon className="size-[18px]" /> : <MoonIcon className="size-[18px]" />}
          {dark ? "Ljust tema" : "Mörkt tema"}
        </button>
      </div>
    </aside>
  )
}

// --- Mobil-meny ---

function MobileNav({
  open,
  onOpenChange,
  dark,
  onToggleDark,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  dark: boolean
  onToggleDark: () => void
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-60 p-0">
        <SheetHeader className="px-5 py-5 border-b">
          <SheetTitle className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
              S
            </div>
            <span className="text-sm font-semibold tracking-tight">
              Systemregister
            </span>
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-0.5 px-3 py-3 flex-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => onOpenChange(false)}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-foreground/70 hover:bg-accent hover:text-accent-foreground",
                ].join(" ")
              }
            >
              <Icon className="size-[18px] shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-3 border-t mt-auto">
          <button
            onClick={onToggleDark}
            className="flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm text-foreground/70 hover:bg-accent hover:text-accent-foreground transition-all duration-150"
          >
            {dark ? <SunIcon className="size-[18px]" /> : <MoonIcon className="size-[18px]" />}
            {dark ? "Ljust tema" : "Mörkt tema"}
          </button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// --- Layout ---

function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dark, setDark] = useDarkMode()

  usePageTitle()
  useKeyboardShortcuts()

  return (
    <div className="flex min-h-screen bg-background transition-theme">
      <SkipLink />
      <KeyboardHelpModal />
      <Sidebar dark={dark} onToggleDark={() => setDark((d) => !d)} />
      <MobileNav
        open={mobileOpen}
        onOpenChange={setMobileOpen}
        dark={dark}
        onToggleDark={() => setDark((d) => !d)}
      />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Mobil-header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b bg-background/80 backdrop-blur-sm sticky top-0 z-40">
          <Button variant="ghost" size="icon-sm" onClick={() => setMobileOpen(true)}>
            <MenuIcon className="size-5" />
            <span className="sr-only">Öppna meny</span>
          </Button>
          <div className="flex items-center gap-2 flex-1">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold text-xs">
              S
            </div>
            <span className="font-semibold text-sm">Systemregister</span>
          </div>
          <NotificationBell />
        </header>

        <main id="main-content" tabIndex={-1} className="flex-1 p-4 md:p-8 overflow-auto">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  )
}

// --- Router ---

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
      { path: "/objekt", element: <ObjektPage /> },
      { path: "/components", element: <ComponentsPage /> },
      { path: "/modules", element: <ModulesPage /> },
      { path: "/information-assets", element: <InformationAssetsPage /> },
      { path: "/approvals", element: <ApprovalsPage /> },
    ],
  },
])

// --- App ---

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  )
}
