"use client"

import { useState } from "react"
import { 
  Tags, Image as ImageIcon, CheckCircle, XCircle, 
  ChevronLeft, ChevronRight, Maximize2, RotateCw,
  Download, Upload, AlertTriangle, Clock
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"

interface QueueItem {
  id: string
  imageId: string
  predictedLabel: string
  confidence: number
  timestamp: string
  status: "pending" | "labeled" | "skipped"
}

export default function LabelingQueuePage() {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null)

  const queueItems: QueueItem[] = [
    { id: "1", imageId: "IMG_20260130_001", predictedLabel: "scratch", confidence: 0.72, timestamp: "2026-01-30T10:15:00", status: "pending" },
    { id: "2", imageId: "IMG_20260130_002", predictedLabel: "dent", confidence: 0.68, timestamp: "2026-01-30T10:16:00", status: "pending" },
    { id: "3", imageId: "IMG_20260130_003", predictedLabel: "normal", confidence: 0.55, timestamp: "2026-01-30T10:17:00", status: "pending" },
    { id: "4", imageId: "IMG_20260130_004", predictedLabel: "crack", confidence: 0.61, timestamp: "2026-01-30T10:18:00", status: "pending" },
    { id: "5", imageId: "IMG_20260130_005", predictedLabel: "stain", confidence: 0.58, timestamp: "2026-01-30T10:19:00", status: "pending" },
  ]

  const labels = ["scratch", "dent", "crack", "stain", "chip", "normal", "other"]
  const currentItem = queueItems[currentIndex]

  const handleNext = () => {
    if (currentIndex < queueItems.length - 1) {
      setCurrentIndex(prev => prev + 1)
      setSelectedLabel(null)
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1)
      setSelectedLabel(null)
    }
  }

  const handleSubmit = () => {
    if (selectedLabel) {
      // Submit label and move to next
      handleNext()
    }
  }

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Labeling Queue</h1>
          <p className="text-sm text-gray-500 mt-1">Review and label low-confidence predictions</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm">
            <Upload className="h-4 w-4" />
            Import Images
          </button>
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm">
            <Download className="h-4 w-4" />
            Export Labels
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard title="In Queue" value={queueItems.length} icon={Clock} color="blue" />
        <StatCard title="Labeled Today" value={156} icon={CheckCircle} color="green" />
        <StatCard title="Skipped" value={12} icon={XCircle} color="gray" />
        <StatCard title="Low Confidence" value={queueItems.filter(i => i.confidence < 0.7).length} icon={AlertTriangle} color="yellow" />
      </div>

      {/* Main Labeling Area */}
      <div className="grid grid-cols-3 gap-6">
        {/* Image Viewer */}
        <div className="col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          {/* Toolbar */}
          <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrev}
                disabled={currentIndex === 0}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg disabled:opacity-50"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {currentIndex + 1} / {queueItems.length}
              </span>
              <button
                onClick={handleNext}
                disabled={currentIndex === queueItems.length - 1}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg disabled:opacity-50"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                <RotateCw className="h-5 w-5 text-gray-500" />
              </button>
              <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                <Maximize2 className="h-5 w-5 text-gray-500" />
              </button>
            </div>
          </div>

          {/* Image Display */}
          <div className="aspect-video bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <div className="text-center">
              <ImageIcon className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <p className="text-sm text-gray-500">{currentItem?.imageId}</p>
              <p className="text-xs text-gray-400 mt-1">No preview available</p>
            </div>
          </div>

          {/* Image Info */}
          <div className="p-4 border-t border-gray-100 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-black dark:text-white">{currentItem?.imageId}</p>
                <p className="text-xs text-gray-500">{currentItem?.timestamp}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Predicted: <span className="font-medium text-black dark:text-white capitalize">{currentItem?.predictedLabel}</span></p>
                <p className="text-xs text-gray-500">Confidence: {((currentItem?.confidence || 0) * 100).toFixed(1)}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Labeling Panel */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider mb-4">
            Select Label
          </h3>

          {/* Label Options */}
          <div className="space-y-2 mb-6">
            {labels.map((label) => (
              <button
                key={label}
                onClick={() => setSelectedLabel(label)}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border transition-all ${
                  selectedLabel === label
                    ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black"
                    : label === currentItem?.predictedLabel
                    ? "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200"
                    : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                }`}
              >
                <span className="capitalize font-medium">{label}</span>
                {label === currentItem?.predictedLabel && (
                  <span className="text-xs bg-blue-200 dark:bg-blue-800 px-2 py-0.5 rounded-full">
                    Predicted
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <button
              onClick={handleSubmit}
              disabled={!selectedLabel}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-black dark:bg-white text-white dark:text-black rounded-lg font-medium disabled:opacity-50"
            >
              <CheckCircle className="h-4 w-4" />
              Submit Label
            </button>
            <button
              onClick={handleNext}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 border border-gray-200 dark:border-gray-800 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <XCircle className="h-4 w-4" />
              Skip
            </button>
          </div>

          {/* Keyboard Shortcuts */}
          <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800">
            <p className="text-xs text-gray-500 mb-2">Keyboard Shortcuts</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">1-7</kbd>
                <span className="text-gray-500">Select label</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">Enter</kbd>
                <span className="text-gray-500">Submit</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">←→</kbd>
                <span className="text-gray-500">Navigate</span>
              </div>
              <div className="flex items-center gap-2">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">S</kbd>
                <span className="text-gray-500">Skip</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Queue List */}
      <div className="mt-6 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
        <div className="p-4 border-b border-gray-100 dark:border-gray-800">
          <h3 className="text-sm font-semibold text-black dark:text-white uppercase tracking-wider">
            Queue ({queueItems.length} items)
          </h3>
        </div>
        <div className="flex gap-2 p-4 overflow-x-auto">
          {queueItems.map((item, index) => (
            <button
              key={item.id}
              onClick={() => setCurrentIndex(index)}
              className={`flex-shrink-0 w-24 h-24 rounded-lg border-2 flex flex-col items-center justify-center transition-all ${
                index === currentIndex
                  ? "border-black dark:border-white bg-gray-50 dark:bg-gray-800"
                  : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
              }`}
            >
              <ImageIcon className="h-8 w-8 text-gray-400 mb-1" />
              <span className="text-xs text-gray-500 truncate w-full px-2 text-center">{item.imageId.slice(-3)}</span>
            </button>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number; icon: React.ElementType; color: string }) {
  const colors = {
    blue: "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
    green: "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400",
    yellow: "bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400",
    gray: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center gap-3">
        <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${colors[color as keyof typeof colors]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">{title}</p>
          <p className="text-xl font-bold text-black dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  )
}
