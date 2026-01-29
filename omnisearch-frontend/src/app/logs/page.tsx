'use client';

import { useState, useCallback } from 'react';
import { DataTable, Badge } from '@/components/ui';
import { formatDateTime, formatPercent, formatMs } from '@/lib/utils';
import { getInspectionLogs, type InspectionLog } from '@/lib/api';
import { useEffect } from 'react';

export default function LogsPage() {
  const [logs, setLogs] = useState<InspectionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    defects_only: false,
    model_name: '',
    limit: 50,
    offset: 0,
  });

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getInspectionLogs(filters);
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (log: InspectionLog) => (
        <span className="font-mono text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
          #{log.id}
        </span>
      ),
    },
    {
      key: 'image_id',
      header: 'Image ID',
      render: (log: InspectionLog) => (
        <span className="font-medium truncate max-w-[150px] block" title={log.image_id}>
          {log.image_id}
        </span>
      ),
    },
    {
      key: 'defect_detected',
      header: 'Status',
      render: (log: InspectionLog) => (
        <Badge variant={log.defect_detected ? 'error' : 'success'}>
          {log.defect_detected ? 'DEFECT' : 'OK'}
        </Badge>
      ),
    },
    {
      key: 'defect_type',
      header: 'Defect Type',
      render: (log: InspectionLog) => (
        <span className="text-sm">{log.defect_type ?? '-'}</span>
      ),
    },
    {
      key: 'model_name',
      header: 'Model',
      render: (log: InspectionLog) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{log.model_name ?? 'N/A'}</span>
      ),
    },
    {
      key: 'confidence_score',
      header: 'Confidence',
      render: (log: InspectionLog) => {
        const score = log.confidence_score;
        const color = score && score > 0.8 ? 'text-green-600' : score && score > 0.5 ? 'text-yellow-600' : 'text-gray-500';
        return <span className={`font-medium ${color}`}>{formatPercent(score ? score * 100 : null)}</span>;
      },
    },
    {
      key: 'inference_time_ms',
      header: 'Inference',
      render: (log: InspectionLog) => (
        <span className="text-sm text-gray-500">{formatMs(log.inference_time_ms)}</span>
      ),
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      render: (log: InspectionLog) => (
        <span className="text-xs text-gray-500">{formatDateTime(log.timestamp)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Inspection Logs</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Browse and filter all inspection records
          </p>
        </div>
        <button
          onClick={fetchLogs}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={filters.defects_only}
              onChange={(e) => setFilters({ ...filters, defects_only: e.target.checked, offset: 0 })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Defects only</span>
          </label>

          <div className="flex items-center">
            <label className="text-sm text-gray-700 dark:text-gray-300 mr-2">Model:</label>
            <input
              type="text"
              value={filters.model_name}
              onChange={(e) => setFilters({ ...filters, model_name: e.target.value, offset: 0 })}
              placeholder="Filter by model..."
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div className="flex items-center">
            <label className="text-sm text-gray-700 dark:text-gray-300 mr-2">Per page:</label>
            <select
              value={filters.limit}
              onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value), offset: 0 })}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-red-800 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Data Table */}
      <DataTable
        data={logs}
        columns={columns}
        keyExtractor={(log) => log.id}
        loading={loading}
        emptyMessage="No inspection logs found"
      />

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Showing {logs.length} records (offset: {filters.offset})
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - filters.limit) })}
            disabled={filters.offset === 0}
            className="px-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Previous
          </button>
          <button
            onClick={() => setFilters({ ...filters, offset: filters.offset + filters.limit })}
            disabled={logs.length < filters.limit}
            className="px-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
