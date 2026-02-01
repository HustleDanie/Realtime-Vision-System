"use client"

import { useState, useEffect } from "react"
import { 
  Server, Cpu, HardDrive, Wifi, Database, 
  Activity, Clock, AlertTriangle, CheckCircle,
  RefreshCw, Settings, Terminal, Zap
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"

interface ServiceStatus {
  name: string
  status: "online" | "offline" | "degraded"
  uptime: string
  latency: number
  version: string
  lastCheck: string
}

interface MetricValue {
  current: number
  max: number
  unit: string
}

export default function SystemHealthPage() {
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [metrics, setMetrics] = useState({
    cpu: { current: 45, max: 100, unit: "%" },
    memory: { current: 6.2, max: 16, unit: "GB" },
    disk: { current: 234, max: 500, unit: "GB" },
    gpu: { current: 72, max: 100, unit: "%" },
    network: { current: 125, max: 1000, unit: "Mbps" },
    requests: { current: 847, max: 1000, unit: "/min" },
  })

  const services: ServiceStatus[] = [
    { name: "Vision API", status: "online", uptime: "99.98%", latency: 23, version: "2.4.1", lastCheck: "10s ago" },
    { name: "Model Server", status: "online", uptime: "99.95%", latency: 45, version: "1.8.0", lastCheck: "10s ago" },
    { name: "Image Processor", status: "online", uptime: "99.92%", latency: 12, version: "3.1.2", lastCheck: "10s ago" },
    { name: "MLflow Registry", status: "online", uptime: "99.99%", latency: 67, version: "2.8.1", lastCheck: "10s ago" },
    { name: "PostgreSQL", status: "online", uptime: "100%", latency: 8, version: "15.2", lastCheck: "10s ago" },
    { name: "Redis Cache", status: "online", uptime: "99.99%", latency: 2, version: "7.2.0", lastCheck: "10s ago" },
    { name: "Prometheus", status: "online", uptime: "99.97%", latency: 15, version: "2.45.0", lastCheck: "10s ago" },
    { name: "Grafana", status: "degraded", uptime: "98.50%", latency: 234, version: "10.1.0", lastCheck: "10s ago" },
  ]

  const handleRefresh = () => {
    setRefreshing(true)
    setTimeout(() => {
      setRefreshing(false)
      setLastUpdated(new Date())
    }, 1000)
  }

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdated(new Date())
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const overallHealth = services.filter(s => s.status === "online").length / services.length * 100

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">System Health</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm">
            <Terminal className="h-4 w-4" />
            View Logs
          </button>
        </div>
      </div>

      {/* Overall Health Banner */}
      <div className={`mb-6 p-6 rounded-lg border ${
        overallHealth === 100 
          ? "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800" 
          : overallHealth >= 90
          ? "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800"
          : "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800"
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {overallHealth === 100 ? (
              <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
            ) : (
              <AlertTriangle className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-black dark:text-white">
                {overallHealth === 100 ? "All Systems Operational" : "Partial Degradation Detected"}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {services.filter(s => s.status === "online").length} of {services.length} services are healthy
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-4xl font-bold text-black dark:text-white">{overallHealth.toFixed(1)}%</p>
            <p className="text-sm text-gray-500">Overall Health</p>
          </div>
        </div>
      </div>

      {/* Resource Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <ResourceCard
          title="CPU Usage"
          icon={Cpu}
          metric={metrics.cpu}
          color="blue"
        />
        <ResourceCard
          title="Memory"
          icon={Server}
          metric={metrics.memory}
          color="purple"
        />
        <ResourceCard
          title="Disk Space"
          icon={HardDrive}
          metric={metrics.disk}
          color="green"
        />
        <ResourceCard
          title="GPU Utilization"
          icon={Zap}
          metric={metrics.gpu}
          color="yellow"
        />
        <ResourceCard
          title="Network"
          icon={Wifi}
          metric={metrics.network}
          color="cyan"
        />
        <ResourceCard
          title="Requests"
          icon={Activity}
          metric={metrics.requests}
          color="pink"
        />
      </div>

      {/* Services Grid */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
        <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
            Service Status
          </h3>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-500" /> Online
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-yellow-500" /> Degraded
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500" /> Offline
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 p-4">
          {services.map((service, index) => (
            <ServiceCard key={index} service={service} />
          ))}
        </div>
      </div>

      {/* Recent Events */}
      <div className="mt-6 grid grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-100 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
              Recent Events
            </h3>
          </div>
          <div className="p-4 space-y-3">
            <EventItem
              time="2 min ago"
              type="warning"
              message="Grafana response time increased to 234ms"
            />
            <EventItem
              time="15 min ago"
              type="success"
              message="Model Server scaled up to 3 replicas"
            />
            <EventItem
              time="1 hour ago"
              type="info"
              message="Daily backup completed successfully"
            />
            <EventItem
              time="2 hours ago"
              type="success"
              message="New model version deployed (v2.4.1)"
            />
            <EventItem
              time="3 hours ago"
              type="warning"
              message="High memory usage detected (85%)"
            />
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-100 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
              Performance Metrics
            </h3>
          </div>
          <div className="p-4 space-y-4">
            <PerformanceMetric
              label="Average Response Time"
              value="45ms"
              target="<100ms"
              status="good"
            />
            <PerformanceMetric
              label="Request Throughput"
              value="847/min"
              target=">500/min"
              status="good"
            />
            <PerformanceMetric
              label="Error Rate"
              value="0.02%"
              target="<0.1%"
              status="good"
            />
            <PerformanceMetric
              label="Model Inference Time"
              value="23ms"
              target="<50ms"
              status="good"
            />
            <PerformanceMetric
              label="Queue Depth"
              value="12"
              target="<50"
              status="good"
            />
          </div>
        </div>
      </div>

      {/* Infrastructure Overview */}
      <div className="mt-6 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
          Infrastructure Overview
        </h3>
        <div className="grid grid-cols-4 gap-4">
          <InfraCard title="Kubernetes Pods" value="12/12" status="healthy" />
          <InfraCard title="Container Replicas" value="8" status="healthy" />
          <InfraCard title="Load Balancers" value="2" status="healthy" />
          <InfraCard title="SSL Certificates" value="Valid" status="healthy" />
        </div>
      </div>
    </DashboardLayout>
  )
}

function ResourceCard({ title, icon: Icon, metric, color }: {
  title: string
  icon: React.ElementType
  metric: MetricValue
  color: string
}) {
  const percentage = (metric.current / metric.max) * 100
  const isHigh = percentage > 80

  const colors = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    cyan: "bg-cyan-500",
    pink: "bg-pink-500",
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-500" />
          <span className="text-sm text-gray-500">{title}</span>
        </div>
        {isHigh && <AlertTriangle className="h-4 w-4 text-yellow-500" />}
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-2xl font-bold text-black dark:text-white">{metric.current}</span>
        <span className="text-sm text-gray-400">/ {metric.max} {metric.unit}</span>
      </div>
      <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ${colors[color as keyof typeof colors]} ${isHigh ? "animate-pulse" : ""}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function ServiceCard({ service }: { service: ServiceStatus }) {
  const statusConfig = {
    online: { color: "bg-green-500", text: "text-green-600 dark:text-green-400", label: "Online" },
    offline: { color: "bg-red-500", text: "text-red-600 dark:text-red-400", label: "Offline" },
    degraded: { color: "bg-yellow-500", text: "text-yellow-600 dark:text-yellow-400", label: "Degraded" },
  }

  const config = statusConfig[service.status]

  return (
    <div className="p-4 rounded-lg border border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${config.color} ${service.status === "online" ? "animate-pulse" : ""}`} />
          <span className="font-medium text-black dark:text-white">{service.name}</span>
        </div>
        <span className={`text-xs font-medium ${config.text}`}>{config.label}</span>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div>
          <p className="text-gray-400">Uptime</p>
          <p className="text-black dark:text-white font-medium">{service.uptime}</p>
        </div>
        <div>
          <p className="text-gray-400">Latency</p>
          <p className="text-black dark:text-white font-medium">{service.latency}ms</p>
        </div>
        <div>
          <p className="text-gray-400">Version</p>
          <p className="text-black dark:text-white font-medium">{service.version}</p>
        </div>
        <div>
          <p className="text-gray-400">Last Check</p>
          <p className="text-black dark:text-white font-medium">{service.lastCheck}</p>
        </div>
      </div>
    </div>
  )
}

function EventItem({ time, type, message }: { time: string; type: "success" | "warning" | "info" | "error"; message: string }) {
  const icons = {
    success: <CheckCircle className="h-4 w-4 text-green-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    info: <Activity className="h-4 w-4 text-blue-500" />,
    error: <AlertTriangle className="h-4 w-4 text-red-500" />,
  }

  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5">{icons[type]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-black dark:text-white">{message}</p>
        <p className="text-xs text-gray-400">{time}</p>
      </div>
    </div>
  )
}

function PerformanceMetric({ label, value, target, status }: { label: string; value: string; target: string; status: "good" | "warning" | "bad" }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-black dark:text-white">{label}</p>
        <p className="text-xs text-gray-400">Target: {target}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-black dark:text-white">{value}</span>
        <span className={`h-2 w-2 rounded-full ${
          status === "good" ? "bg-green-500" : status === "warning" ? "bg-yellow-500" : "bg-red-500"
        }`} />
      </div>
    </div>
  )
}

function InfraCard({ title, value, status }: { title: string; value: string; status: "healthy" | "warning" | "unhealthy" }) {
  return (
    <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
      <p className="text-xs text-gray-500 mb-1">{title}</p>
      <div className="flex items-center justify-between">
        <span className="text-lg font-semibold text-black dark:text-white">{value}</span>
        <span className={`h-2 w-2 rounded-full ${
          status === "healthy" ? "bg-green-500" : status === "warning" ? "bg-yellow-500" : "bg-red-500"
        }`} />
      </div>
    </div>
  )
}
