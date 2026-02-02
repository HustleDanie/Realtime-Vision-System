"use client"

import { useState, useEffect, useCallback } from "react"
import { 
  Search, Filter, RefreshCw, Download, ChevronLeft, ChevronRight,
  CheckCircle, XCircle, Eye, Clock, Image as ImageIcon
} from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { getInspectionLogs, type InspectionLog } from "@/lib/api"

export default function InspectionsPage() {
  const [logs, setLogs] = useState<InspectionLog[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | "defect" | "ok">("all")
  const [pagination, setPagination] = useState({ offset: 0, limit: 20 })

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getInspectionLogs({
        defects_only: statusFilter === "defect",
        limit: pagination.limit,
        offset: pagination.offset,
      })
      setLogs(data)
    } catch (err) {
      console.error("Failed to fetch logs:", err)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, pagination])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const filteredLogs = logs.filter((log) => {
    if (statusFilter === "defect" && !log.defect_detected) return false
    if (statusFilter === "ok" && log.defect_detected) return false
    if (search && !log.image_id.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-black dark:text-white">Inspections</h1>
          <p className="text-sm text-gray-500 mt-1">View all inspection results and defect history</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium hover:opacity-80 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by image ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "all" | "defect" | "ok")}
            className="pl-10 pr-8 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
          >
            <option value="all">All Results</option>
            <option value="defect">Defects Only</option>
            <option value="ok">Passed Only</option>
          </select>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Total</p>
          <p className="text-2xl font-bold text-black dark:text-white">{logs.length}</p>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Defects</p>
          <p className="text-2xl font-bold text-red-600">{logs.filter(l => l.defect_detected).length}</p>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Passed</p>
          <p className="text-2xl font-bold text-green-600">{logs.filter(l => !l.defect_detected).length}</p>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Avg Confidence</p>
          <p className="text-2xl font-bold text-black dark:text-white">
            {logs.length > 0 ? `${(logs.reduce((a, l) => a + (l.confidence_score || 0), 0) / logs.length * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800/50">
            <tr>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Image</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Inference</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
              <th className="text-left py-4 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td colSpan={8} className="py-4 px-6"><div className="h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" /></td>
                </tr>
              ))
            ) : filteredLogs.length > 0 ? (
              filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="py-4 px-6 text-sm font-mono text-gray-500">#{log.id}</td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                        <ImageIcon className="h-5 w-5 text-gray-400" />
                      </div>
                      <span className="text-sm font-medium text-black dark:text-white truncate max-w-[120px]">{log.image_id}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    {log.defect_detected ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                        <XCircle className="h-3 w-3" /> Defect
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        <CheckCircle className="h-3 w-3" /> Passed
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${(log.confidence_score || 0) > 0.8 ? 'bg-green-500' : (log.confidence_score || 0) > 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${(log.confidence_score || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-black dark:text-white">{((log.confidence_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm text-gray-600 dark:text-gray-400">{log.model_name || 'N/A'}</td>
                  <td className="py-4 px-6">
                    <span className="text-sm font-mono text-gray-600 dark:text-gray-400">{log.inference_time_ms?.toFixed(0) || '—'}ms</span>
                  </td>
                  <td className="py-4 px-6">
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                      <Eye className="h-4 w-4 text-gray-500" />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="py-12 text-center">
                  <ImageIcon className="h-12 w-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                  <p className="text-gray-500">No inspections found</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <p className="text-sm text-gray-500">Showing {filteredLogs.length} results</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPagination(p => ({ ...p, offset: Math.max(0, p.offset - p.limit) }))}
              disabled={pagination.offset === 0}
              className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 dark:border-gray-800 rounded-lg text-sm disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <button
              onClick={() => setPagination(p => ({ ...p, offset: p.offset + p.limit }))}
              disabled={logs.length < pagination.limit}
              className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 dark:border-gray-800 rounded-lg text-sm disabled:opacity-50"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
