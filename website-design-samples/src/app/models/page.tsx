"use client"

import { useState } from "react"
import { 
  Brain, Upload, Download, RefreshCw, Play, Pause,
  CheckCircle, Clock, GitBranch, Layers, Settings,
  TrendingUp, AlertTriangle
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { StatusIndicator } from "@/components/ui/status-indicator"

interface ModelInfo {
  id: string
  name: string
  version: string
  status: "active" | "staging" | "archived"
  accuracy: number
  createdAt: string
  predictions: number
  framework: string
}

export default function ModelsPage() {
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  const models: ModelInfo[] = [
    {
      id: "1",
      name: "YOLOv8-DefectDetector",
      version: "v2.1.0",
      status: "active",
      accuracy: 98.5,
      createdAt: "2026-01-15",
      predictions: 156789,
      framework: "PyTorch",
    },
    {
      id: "2",
      name: "YOLOv8-DefectDetector",
      version: "v2.0.0",
      status: "staging",
      accuracy: 97.2,
      createdAt: "2026-01-01",
      predictions: 89234,
      framework: "PyTorch",
    },
    {
      id: "3",
      name: "YOLOv8-DefectDetector",
      version: "v1.5.0",
      status: "archived",
      accuracy: 95.8,
      createdAt: "2025-12-01",
      predictions: 234567,
      framework: "PyTorch",
    },
  ]

  const activeModel = models.find(m => m.status === "active")

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Models</h1>
          <p className="text-sm text-gray-500 mt-1">Manage and deploy ML models for defect detection</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm">
            <Upload className="h-4 w-4" />
            Upload Model
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium">
            <RefreshCw className="h-4 w-4" />
            Sync MLflow
          </button>
        </div>
      </div>

      {/* Active Model Card */}
      {activeModel && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <Brain className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-black dark:text-white">{activeModel.name}</h2>
                <p className="text-sm text-gray-500">Production Model</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded-full text-sm font-medium">
                <StatusIndicator status="online" size="sm" pulse={true} />
                Active
              </span>
              <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                <Settings className="h-5 w-5 text-gray-500" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-6">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Version</p>
              <p className="text-lg font-bold text-black dark:text-white">{activeModel.version}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Accuracy</p>
              <p className="text-lg font-bold text-green-600">{activeModel.accuracy}%</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Predictions</p>
              <p className="text-lg font-bold text-black dark:text-white">{activeModel.predictions.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Framework</p>
              <p className="text-lg font-bold text-black dark:text-white">{activeModel.framework}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Deployed</p>
              <p className="text-lg font-bold text-black dark:text-white">{activeModel.createdAt}</p>
            </div>
          </div>
        </div>
      )}

      {/* Model Grid */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Model Registry */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-100 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
              Model Registry
            </h3>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {models.map((model) => (
              <div
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                  selectedModel === model.id ? "bg-gray-50 dark:bg-gray-800/50" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      model.status === "active" 
                        ? "bg-green-100 dark:bg-green-900/30" 
                        : model.status === "staging"
                        ? "bg-yellow-100 dark:bg-yellow-900/30"
                        : "bg-gray-100 dark:bg-gray-800"
                    }`}>
                      <Brain className={`h-5 w-5 ${
                        model.status === "active" 
                          ? "text-green-600 dark:text-green-400" 
                          : model.status === "staging"
                          ? "text-yellow-600 dark:text-yellow-400"
                          : "text-gray-500"
                      }`} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-black dark:text-white">{model.version}</p>
                      <p className="text-xs text-gray-500">{model.predictions.toLocaleString()} predictions</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                    model.status === "active" 
                      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" 
                      : model.status === "staging"
                      ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  }`}>
                    {model.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Model Performance */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-6">
            Performance Metrics
          </h3>
          
          <div className="space-y-6">
            <MetricBar label="Accuracy" value={98.5} target={95} />
            <MetricBar label="Precision" value={97.2} target={90} />
            <MetricBar label="Recall" value={96.8} target={90} />
            <MetricBar label="F1 Score" value={97.0} target={90} />
          </div>

          <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Avg Latency</p>
                <p className="text-lg font-bold text-black dark:text-white">45ms</p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Throughput</p>
                <p className="text-lg font-bold text-black dark:text-white">22 FPS</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Model Actions */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <ActionButton icon={Play} label="Test Model" />
          <ActionButton icon={GitBranch} label="Compare Versions" />
          <ActionButton icon={Download} label="Export Model" />
          <ActionButton icon={Layers} label="View Layers" />
          <ActionButton icon={TrendingUp} label="Training History" />
        </div>
      </div>
    </DashboardLayout>
  )
}

function MetricBar({ label, value, target }: { label: string; value: number; target: number }) {
  const isAboveTarget = value >= target
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
        <span className={`text-sm font-mono font-bold ${isAboveTarget ? "text-green-600" : "text-red-600"}`}>
          {value}%
        </span>
      </div>
      <div className="relative h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${isAboveTarget ? "bg-green-500" : "bg-red-500"}`}
          style={{ width: `${value}%` }}
        />
        <div
          className="absolute top-0 h-full w-0.5 bg-black dark:bg-white"
          style={{ left: `${target}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">Target: {target}%</p>
    </div>
  )
}

function ActionButton({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <button className="flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
}
