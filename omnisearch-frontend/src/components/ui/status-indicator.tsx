"use client"

import { cn } from "@/lib/utils"

type StatusType = "online" | "offline" | "warning" | "loading"

interface StatusIndicatorProps {
  status: StatusType
  label?: string
  size?: "sm" | "md" | "lg"
  pulse?: boolean
}

const statusColors: Record<StatusType, string> = {
  online: "bg-green-500",
  offline: "bg-red-500",
  warning: "bg-yellow-500",
  loading: "bg-gray-400",
}

const statusLabels: Record<StatusType, string> = {
  online: "Online",
  offline: "Offline",
  warning: "Warning",
  loading: "Loading",
}

const sizes = {
  sm: "h-2 w-2",
  md: "h-3 w-3",
  lg: "h-4 w-4",
}

export function StatusIndicator({ 
  status, 
  label, 
  size = "md",
  pulse = true 
}: StatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex">
        <span
          className={cn(
            "rounded-full",
            sizes[size],
            statusColors[status],
            pulse && status === "online" && "animate-pulse"
          )}
        />
        {pulse && status === "online" && (
          <span
            className={cn(
              "absolute inset-0 rounded-full opacity-75 animate-ping",
              statusColors[status]
            )}
          />
        )}
      </span>
      {label !== undefined && (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {label || statusLabels[status]}
        </span>
      )}
    </div>
  )
}
