"use client"

import { useState } from "react"
import { 
  BarChart3, TrendingUp, TrendingDown, Calendar,
  Download, RefreshCw, AlertTriangle, CheckCircle
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState("7d")

  // Mock data
  const weeklyData = [
    { day: "Mon", inspections: 2340, defects: 156 },
    { day: "Tue", inspections: 2780, defects: 189 },
    { day: "Wed", inspections: 2450, defects: 134 },
    { day: "Thu", inspections: 3100, defects: 245 },
    { day: "Fri", inspections: 2890, defects: 178 },
    { day: "Sat", inspections: 1200, defects: 67 },
    { day: "Sun", inspections: 800, defects: 42 },
  ]

  const defectTypes = [
    { type: "Scratch", count: 423, percentage: 35 },
    { type: "Dent", count: 289, percentage: 24 },
    { type: "Crack", count: 198, percentage: 16 },
    { type: "Stain", count: 156, percentage: 13 },
    { type: "Chip", count: 89, percentage: 7 },
    { type: "Other", count: 56, percentage: 5 },
  ]

  const maxInspections = Math.max(...weeklyData.map(d => d.inspections))

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Inspection trends and defect analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            {["24h", "7d", "30d", "90d"].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  timeRange === range
                    ? "bg-black dark:bg-white text-white dark:text-black"
                    : "text-gray-600 dark:text-gray-400 hover:text-black dark:hover:text-white"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm">
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Total Inspections"
          value="15,560"
          change={12.5}
          positive={true}
          icon={BarChart3}
        />
        <StatCard
          title="Total Defects"
          value="1,011"
          change={-3.2}
          positive={true}
          icon={AlertTriangle}
        />
        <StatCard
          title="Pass Rate"
          value="93.5%"
          change={1.8}
          positive={true}
          icon={CheckCircle}
        />
        <StatCard
          title="Avg Confidence"
          value="94.2%"
          change={0.5}
          positive={true}
          icon={TrendingUp}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        {/* Inspection Trend Chart */}
        <div className="col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
              Inspection Volume
            </h3>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded bg-black dark:bg-white" />
                Inspections
              </span>
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded bg-red-500" />
                Defects
              </span>
            </div>
          </div>
          
          {/* Bar Chart */}
          <div className="h-64 flex items-end gap-4">
            {weeklyData.map((data) => (
              <div key={data.day} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full flex flex-col items-center gap-1" style={{ height: '200px' }}>
                  <div
                    className="w-full bg-black dark:bg-white rounded-t transition-all"
                    style={{ height: `${(data.inspections / maxInspections) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500">{data.day}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Defect Types */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-6">
            Defect Distribution
          </h3>
          
          <div className="space-y-4">
            {defectTypes.map((defect) => (
              <div key={defect.type}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-600 dark:text-gray-400">{defect.type}</span>
                  <span className="text-sm font-mono text-black dark:text-white">{defect.count}</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-black dark:bg-white rounded-full"
                    style={{ width: `${defect.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hourly Distribution */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-6">
          Hourly Distribution
        </h3>
        
        <div className="h-32 flex items-end gap-1">
          {Array.from({ length: 24 }, (_, i) => {
            const value = Math.random() * 100 + 20
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-gray-300 dark:bg-gray-700 hover:bg-black dark:hover:bg-white transition-colors rounded-t"
                  style={{ height: `${value}%` }}
                />
              </div>
            )
          })}
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-400">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </div>
    </DashboardLayout>
  )
}

function StatCard({ 
  title, 
  value, 
  change, 
  positive, 
  icon: Icon 
}: { 
  title: string
  value: string
  change: number
  positive: boolean
  icon: React.ElementType
}) {
  const isUp = change > 0
  
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500 uppercase tracking-wider">{title}</span>
        <Icon className="h-4 w-4 text-gray-400" />
      </div>
      <p className="text-2xl font-bold text-black dark:text-white mb-1">{value}</p>
      <div className={`flex items-center gap-1 text-xs ${positive ? 'text-green-600' : 'text-red-600'}`}>
        {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
        <span>{Math.abs(change)}% vs last period</span>
      </div>
    </div>
  )
}
