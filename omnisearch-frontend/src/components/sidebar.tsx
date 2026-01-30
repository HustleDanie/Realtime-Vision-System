"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  LayoutDashboard, Search, BarChart3, Brain, 
  Tags, Activity, HeartPulse, Settings, LogOut, Eye,
  Video
} from "lucide-react"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/new-inspection", label: "Video Inspection", icon: Video },
  { href: "/inspections", label: "Inspections", icon: Search },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/models", label: "Models", icon: Brain },
  { href: "/labeling-queue", label: "Labeling Queue", icon: Tags },
  { href: "/drift-monitoring", label: "Drift Monitoring", icon: Activity },
  { href: "/system-health", label: "System Health", icon: HeartPulse },
]

const bottomItems = [
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/logout", label: "Log Out", icon: LogOut },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-black text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <Link href="/" className="flex items-center gap-3">
          <Eye className="h-6 w-6" />
          <span className="text-lg font-bold tracking-tight">Defect Detector</span>
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-4">
        <ul className="space-y-1 px-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive
                      ? "bg-white text-black font-medium"
                      : "text-gray-400 hover:text-white hover:bg-gray-900"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Bottom Navigation */}
      <div className="py-4 border-t border-gray-800">
        <ul className="space-y-1 px-3">
          {bottomItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive
                      ? "bg-white text-black font-medium"
                      : "text-gray-400 hover:text-white hover:bg-gray-900"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </aside>
  )
}
