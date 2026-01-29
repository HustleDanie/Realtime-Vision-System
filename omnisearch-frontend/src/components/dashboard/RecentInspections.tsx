'use client';

import { useLatestLogs } from '@/lib/hooks';
import { DataTable, Badge } from '@/components/ui';
import { formatDateTime, formatPercent, formatMs } from '@/lib/utils';
import type { InspectionLog } from '@/lib/api';

export function RecentInspections() {
  const { data: logs, loading, error } = useLatestLogs(10);

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (log: InspectionLog) => (
        <span className="font-mono text-xs">{log.id}</span>
      ),
    },
    {
      key: 'image_id',
      header: 'Image',
      render: (log: InspectionLog) => (
        <span className="font-medium truncate max-w-[120px] block" title={log.image_id}>
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
      header: 'Type',
      render: (log: InspectionLog) => (
        <span className="text-sm">{log.defect_type ?? '-'}</span>
      ),
    },
    {
      key: 'confidence_score',
      header: 'Confidence',
      render: (log: InspectionLog) => (
        <span className={`font-medium ${
          log.confidence_score && log.confidence_score > 0.8 ? 'text-green-600' :
          log.confidence_score && log.confidence_score > 0.5 ? 'text-yellow-600' : 'text-gray-500'
        }`}>
          {formatPercent(log.confidence_score ? log.confidence_score * 100 : null)}
        </span>
      ),
    },
    {
      key: 'inference_time_ms',
      header: 'Time',
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

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Inspections</h3>
        <p className="text-red-600 dark:text-red-400">Failed to load: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Inspections</h3>
        <a href="/logs" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
          View all →
        </a>
      </div>
      <DataTable
        data={logs ?? []}
        columns={columns}
        keyExtractor={(log) => log.id}
        loading={loading}
        emptyMessage="No inspection logs yet"
      />
    </div>
  );
}
