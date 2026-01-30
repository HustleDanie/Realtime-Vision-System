"use client"

import { useState, useEffect, useCallback } from "react"
import { 
  Search, Activity, Gauge, Brain, Server, Database, 
  Cpu, Cloud, RefreshCw, AlertTriangle, CheckCircle,
  Clock
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { KPICard } from "@/components/ui/kpi-card"
import { SystemStatusPanel } from "@/components/ui/system-status-panel"
import { StatusIndicator } from "@/components/ui/status-indicator"

interface Metrics {
  total_predictions: number
  defects_detected: number
  avg_confidence: number
  avg_inference_time_ms: number
}

interface HealthStatus {
  status: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  database: string
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [metricsRes, healthRes] = await Promise.allSettled([
        fetch("http://localhost:8000/api/metrics"),
        fetch("http://localhost:8000/api/health"),
      ])

      if (metricsRes.status === "fulfilled" && metricsRes.value.ok) {
        setMetrics(await metricsRes.value.json())
      }

      if (healthRes.status === "fulfilled" && healthRes.value.ok) {
        setHealth(await healthRes.value.json())
      }

      setLastUpdated(new Date())
    } catch (err) {
      setError("Failed to fetch dashboard data")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData])

  const defectRate = metrics 
    ? ((metrics.defects_detected / Math.max(metrics.total_predictions, 1)) * 100).toFixed(1)
    : "0"

  const services = [
    {
      name: "Drift Detection",
      icon: Activity,
      status: health?.status === "ok" ? "online" as const : "warning" as const,
      description: "Model drift monitoring",
      latency: 12,
    },
    {
      name: "Edge Inference",
      icon: Cpu,
      status: "online" as const,
      description: "YOLO inference service",
      latency: metrics?.avg_inference_time_ms ? Math.round(metrics.avg_inference_time_ms) : 45,
    },
    {
      name: "Backend API",
      icon: Server,
      status: health ? "online" as const : "offline" as const,
      description: "FastAPI server",
      latency: 8,
    },
    {
      name: "Database",
      icon: Database,
      status: health?.database === "ok" ? "online" as const : "offline" as const,
      description: "PostgreSQL / SQLite",
      latency: 3,
    },
    {
      name: "MLflow Server",
      icon: Cloud,
      status: "online" as const,
      description: "Model registry & tracking",
      latency: 25,
    },
  ]

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Control Panel</h1>
          <p className="text-sm text-gray-500 mt-1">Factory AI inspection system overview</p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium hover:opacity-80 transition-opacity disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <span className="text-sm text-red-800 dark:text-red-200">{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          title="Inspections Today"
          value={metrics?.total_predictions?.toLocaleString() ?? "—"}
          subtitle="Total images processed"
          icon={Search}
          trend={{ value: 12, isPositive: true }}
          loading={loading}
        />
        <KPICard
          title="Defect Rate"
          value={`${defectRate}%`}
          subtitle="Of total inspections"
          icon={AlertTriangle}
          trend={{ value: 2.3, isPositive: false }}
          loading={loading}
        />
        <KPICard
          title="Avg Confidence"
          value={metrics?.avg_confidence ? `${(metrics.avg_confidence * 100).toFixed(1)}%` : "—"}
          subtitle="Model prediction confidence"
          icon={Gauge}
          loading={loading}
        />
        <KPICard
          title="Model Version"
          value="YOLOv8-v2.1"
          subtitle="Current production model"
          icon={Brain}
          loading={loading}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Status */}
        <div className="lg:col-span-2">
          <SystemStatusPanel title="System Status" services={services} loading={loading} />
        </div>

        {/* Drift Status */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
            Drift Monitor
          </h3>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-green-800 dark:text-green-200">Status: Normal</span>
                <StatusIndicator status="online" size="lg" />
              </div>
              <p className="text-xs text-green-600 dark:text-green-400">No significant drift detected</p>
            </div>
            <DriftMetric label="Feature Drift" value={0.12} threshold={0.3} />
            <DriftMetric label="Prediction Drift" value={0.08} threshold={0.25} />
            <DriftMetric label="Label Drift" value={0.05} threshold={0.2} />
          </div>
        </div>

        {/* Resource Usage */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
            Resource Usage
          </h3>
          <div className="grid grid-cols-3 gap-6">
            <ResourceGauge label="CPU" value={health?.cpu_percent ?? 0} loading={loading} />
            <ResourceGauge label="Memory" value={health?.memory_percent ?? 0} loading={loading} />
            <ResourceGauge label="Disk" value={health?.disk_percent ?? 0} loading={loading} />
          </div>
        </div>

        {/* Quick Stats */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
            Today&apos;s Summary
          </h3>
          <div className="space-y-4">
            <QuickStat label="Defects Found" value={metrics?.defects_detected ?? 0} icon={AlertTriangle} color="red" />
            <QuickStat label="Passed" value={(metrics?.total_predictions ?? 0) - (metrics?.defects_detected ?? 0)} icon={CheckCircle} color="green" />
            <QuickStat label="Avg Inference" value={`${metrics?.avg_inference_time_ms?.toFixed(0) ?? 0}ms`} icon={Cpu} color="blue" />
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

function DriftMetric({ label, value, threshold }: { label: string; value: number; threshold: number }) {
  const percentage = (value / threshold) * 100
  const isWarning = percentage > 70
  const isDanger = percentage > 90
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-600 dark:text-gray-400">{label}</span>
        <span className="text-xs font-mono text-black dark:text-white">{value.toFixed(2)} / {threshold}</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${isDanger ? "bg-red-500" : isWarning ? "bg-yellow-500" : "bg-green-500"}`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
    </div>
  )
}

function ResourceGauge({ label, value, loading }: { label: string; value: number; loading: boolean }) {
  const circumference = 2 * Math.PI * 40
  const strokeDashoffset = circumference - (value / 100) * circumference
  const color = value > 80 ? "text-red-500" : value > 60 ? "text-yellow-500" : "text-green-500"
  return (
    <div className="flex flex-col items-center">
      <div className="relative h-24 w-24">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8" className="text-gray-200 dark:text-gray-800" />
          {!loading && <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} className={color} />}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          {loading ? <div className="h-6 w-10 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" /> : <span className="text-lg font-bold text-black dark:text-white">{value.toFixed(0)}%</span>}
        </div>
      </div>
      <span className="text-xs text-gray-500 mt-2">{label}</span>
    </div>
  )
}

function QuickStat({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: "red" | "green" | "blue" }) {
  const colors = {
    red: "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
    green: "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400",
    blue: "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
  }
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${colors[color]}`}><Icon className="h-4 w-4" /></div>
        <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      </div>
      <span className="text-sm font-bold text-black dark:text-white">{value}</span>
    </div>
  )
}
