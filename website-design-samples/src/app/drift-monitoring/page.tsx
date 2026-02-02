"use client"

import { useState, useEffect } from "react"
import { 
  AlertTriangle, TrendingUp, TrendingDown, RefreshCw,
  Layers, Activity, BarChart3, Calendar,
  CheckCircle, XCircle, AlertCircle, Info
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"

interface DriftMetric {
  feature: string
  baseline: number
  current: number
  drift: number
  status: "normal" | "warning" | "critical"
}

export default function DriftMonitoringPage() {
  const [timeRange, setTimeRange] = useState("24h")
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const driftMetrics: DriftMetric[] = [
    { feature: "Brightness", baseline: 0.52, current: 0.54, drift: 3.8, status: "normal" },
    { feature: "Contrast", baseline: 0.48, current: 0.51, drift: 6.2, status: "normal" },
    { feature: "Sharpness", baseline: 0.71, current: 0.68, drift: -4.2, status: "normal" },
    { feature: "Color Distribution", baseline: 0.45, current: 0.39, drift: -13.3, status: "warning" },
    { feature: "Edge Density", baseline: 0.63, current: 0.61, drift: -3.2, status: "normal" },
    { feature: "Texture Variance", baseline: 0.38, current: 0.29, drift: -23.7, status: "critical" },
    { feature: "Object Size", baseline: 0.55, current: 0.53, drift: -3.6, status: "normal" },
    { feature: "Background Uniformity", baseline: 0.82, current: 0.79, drift: -3.7, status: "normal" },
  ]

  const handleRefresh = () => {
    setRefreshing(true)
    setTimeout(() => {
      setRefreshing(false)
      setLastUpdated(new Date())
    }, 1000)
  }

  const overallDriftScore = 0.23 // 0-1 scale
  const driftStatus = overallDriftScore < 0.15 ? "healthy" : overallDriftScore < 0.3 ? "warning" : "critical"

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Drift Monitoring</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 text-sm"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Drift Score */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Overall Drift Score</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              driftStatus === "healthy" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
              driftStatus === "warning" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
              "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
            }`}>
              {driftStatus.toUpperCase()}
            </span>
          </div>
          <div className="flex items-end gap-4">
            <span className="text-5xl font-bold text-black dark:text-white">{(overallDriftScore * 100).toFixed(1)}%</span>
            <div className="pb-2">
              <div className="flex items-center gap-1 text-yellow-600">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm">+2.3% from baseline</span>
              </div>
            </div>
          </div>
          {/* Drift Score Bar */}
          <div className="mt-4">
            <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-500 ${
                  driftStatus === "healthy" ? "bg-green-500" :
                  driftStatus === "warning" ? "bg-yellow-500" : "bg-red-500"
                }`}
                style={{ width: `${overallDriftScore * 100}%` }}
              />
            </div>
            <div className="flex justify-between mt-1 text-xs text-gray-400">
              <span>0%</span>
              <span>15% (Warning)</span>
              <span>30% (Critical)</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        <DriftStatCard
          title="Feature Drift"
          value="2"
          subtitle="features affected"
          icon={Layers}
          status="warning"
        />
        <DriftStatCard
          title="Prediction Drift"
          value="1.2%"
          subtitle="accuracy delta"
          icon={BarChart3}
          status="normal"
        />
      </div>

      {/* Drift Types */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <DriftTypeCard
          title="Data Drift"
          description="Changes in input feature distributions"
          score={18}
          threshold={15}
          status="warning"
        />
        <DriftTypeCard
          title="Concept Drift"
          description="Changes in relationship between features and target"
          score={8}
          threshold={15}
          status="normal"
        />
        <DriftTypeCard
          title="Label Drift"
          description="Changes in the target variable distribution"
          score={5}
          threshold={15}
          status="normal"
        />
      </div>

      {/* Feature Drift Table */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
        <div className="p-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
              Feature-Level Drift Analysis
            </h3>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500" /> Normal</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-yellow-500" /> Warning</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" /> Critical</span>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Feature</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Baseline</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Current</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Drift %</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trend</th>
              </tr>
            </thead>
            <tbody>
              {driftMetrics.map((metric, index) => (
                <tr key={index} className="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <span className="font-medium text-black dark:text-white">{metric.feature}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{metric.baseline.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{metric.current.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${
                      metric.drift > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                    }`}>
                      {metric.drift > 0 ? "+" : ""}{metric.drift.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      metric.status === "normal" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                      metric.status === "warning" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    }`}>
                      {metric.status === "normal" ? <CheckCircle className="h-3 w-3" /> :
                       metric.status === "warning" ? <AlertCircle className="h-3 w-3" /> :
                       <XCircle className="h-3 w-3" />}
                      {metric.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {metric.drift > 0 ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drift History Chart Placeholder */}
      <div className="mt-6 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
          Drift Score History
        </h3>
        <div className="h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-center">
            <Activity className="h-12 w-12 mx-auto text-gray-400 mb-2" />
            <p className="text-sm text-gray-500">Drift history chart</p>
            <p className="text-xs text-gray-400">Shows drift score over time</p>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="mt-6 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Info className="h-5 w-5 text-blue-500" />
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
            Recommendations
          </h3>
        </div>
        <div className="space-y-3">
          <RecommendationItem
            type="warning"
            title="Texture Variance drift detected"
            description="The texture variance feature has drifted by -23.7%. Consider investigating the source images for quality issues or camera calibration."
          />
          <RecommendationItem
            type="warning"
            title="Color Distribution shift observed"
            description="Color distribution has shifted by -13.3%. This may affect defect detection accuracy for color-based anomalies."
          />
          <RecommendationItem
            type="info"
            title="Model retraining suggested"
            description="Based on current drift levels, consider scheduling a model retraining cycle within the next 7 days to maintain optimal performance."
          />
        </div>
      </div>
    </DashboardLayout>
  )
}

function DriftStatCard({ title, value, subtitle, icon: Icon, status }: { 
  title: string
  value: string
  subtitle: string
  icon: React.ElementType
  status: "normal" | "warning" | "critical"
}) {
  const statusColors = {
    normal: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    critical: "text-red-600 dark:text-red-400",
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center gap-3 mb-3">
        <Icon className={`h-5 w-5 ${statusColors[status]}`} />
        <span className="text-sm text-gray-500">{title}</span>
      </div>
      <p className="text-3xl font-bold text-black dark:text-white">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
    </div>
  )
}

function DriftTypeCard({ title, description, score, threshold, status }: {
  title: string
  description: string
  score: number
  threshold: number
  status: "normal" | "warning" | "critical"
}) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-black dark:text-white">{title}</h4>
        <span className={`h-3 w-3 rounded-full ${
          status === "normal" ? "bg-green-500" :
          status === "warning" ? "bg-yellow-500" : "bg-red-500"
        }`} />
      </div>
      <p className="text-xs text-gray-500 mb-4">{description}</p>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Current Score</span>
          <span className="font-medium text-black dark:text-white">{score}%</span>
        </div>
        <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div 
            className={`h-full ${
              status === "normal" ? "bg-green-500" :
              status === "warning" ? "bg-yellow-500" : "bg-red-500"
            }`}
            style={{ width: `${Math.min(score, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400">
          <span>0%</span>
          <span>Threshold: {threshold}%</span>
        </div>
      </div>
    </div>
  )
}

function RecommendationItem({ type, title, description }: {
  type: "info" | "warning" | "error"
  title: string
  description: string
}) {
  const styles = {
    info: "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20",
    warning: "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20",
    error: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
  }

  const icons = {
    info: <Info className="h-4 w-4 text-blue-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    error: <XCircle className="h-4 w-4 text-red-500" />,
  }

  return (
    <div className={`p-4 rounded-lg border ${styles[type]}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{icons[type]}</div>
        <div>
          <p className="font-medium text-black dark:text-white">{title}</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{description}</p>
        </div>
      </div>
    </div>
  )
}
