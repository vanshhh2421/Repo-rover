import { Link, useLocation } from "react-router-dom"
import { Database, LayoutDashboard, Sun, Moon } from "lucide-react"
import { useTheme } from "./ThemeProvider"
import { cn } from "../lib/utils"

export default function Sidebar() {
  const { pathname } = useLocation()
  const { theme, setTheme } = useTheme()

  const links = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Repositories", href: "/", icon: Database },
  ]

  return (
    <aside className="w-64 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-zinc-200 dark:border-zinc-800">
        <Database className="w-6 h-6 mr-2 text-blue-600 dark:text-blue-400" />
        <span className="font-semibold tracking-tight">RepoRover</span>
      </div>

      <nav className="flex-1 py-6 px-4 space-y-1">
        {links.map((link) => {
          const Icon = link.icon
          const isActive = pathname === link.href
          return (
            <Link
              key={link.name}
              to={link.href}
              className={cn(
                "flex items-center px-3 py-2 text-sm rounded-md transition-colors",
                isActive
                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium"
                  : "text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100"
              )}
            >
              <Icon className="w-4 h-4 mr-3" />
              {link.name}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
        <span className="text-xs text-zinc-400">RepoRover v0.1</span>
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  )
}
