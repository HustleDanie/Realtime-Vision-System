"use client"

import { cn } from "@/lib/utils"
import { LucideIcon } from "lucide-react"
import { StatusIndicator } from "./status-indicator"

type ServiceStatus = "online" | "offline" | "warning" | "loading"

interface ServiceItem {
  name: string
  icon: LucideIcon
  status: ServiceStatus
  latency?: number
  description?: string
}

interface SystemStatusPanelProps {
  title?: string
  services: ServiceItem[]
  loading?: boolean
  className?: string
}

export function SystemStatusPanel({
  title = "System Status",
  services,
  loading = false,
  className,
}: SystemStatusPanelProps) {
  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800",
        className
      )}
    >
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
          {title}
        </h3>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {loading ? (
          [...Array(5)].map((_, i) => (
            <div key={i} className="px-5 py-4">
              <div className="h-5 w-32 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
            </div>
          ))
        ) : (
          services.map((service) => (
            <div
              key={service.name}
              className="px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <service.icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-black dark:text-white">
                    {service.name}
                  </p>
                  {service.description && (
                    <p className="text-xs text-gray-500">{service.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4">
                {service.latency !== undefined && service.status === "online" && (
                  <span className="text-xs text-gray-500 font-mono">
                    {service.latency}ms
                  </span>
                )}
                <StatusIndicator status={service.status} size="md" />
                <span
                  className={cn(
                    "text-xs font-medium px-2 py-1 rounded-full",
                    service.status === "online" && "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                    service.status === "offline" && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                    service.status === "warning" && "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
                    service.status === "loading" && "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400"
                  )}
                >
                  {service.status === "online" ? "Operational" : 
                   service.status === "offline" ? "Down" : 
                   service.status === "warning" ? "Degraded" : "Checking..."}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
