'use client';

import { useHealth } from '@/lib/hooks';
import { StatusCard } from '@/components/ui';
import { ProgressBar } from '@/components/ui';
import { formatPercent, formatDateTime } from '@/lib/utils';

export function HealthStatus() {
  const { data: health, loading, error } = useHealth();

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <StatusCard
        title="System Health"
        status="error"
        details={{ Error: error }}
      />
    );
  }

  const status = health?.status === 'ok' ? 'ok' : health?.status === 'degraded' ? 'degraded' : 'error';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">System Health</h3>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          status === 'ok' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
          status === 'degraded' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
          'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
        }`}>
          <span className={`w-2 h-2 rounded-full mr-2 ${
            status === 'ok' ? 'bg-green-500' : status === 'degraded' ? 'bg-orange-500' : 'bg-red-500'
          }`}></span>
          {status.toUpperCase()}
        </span>
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-500 dark:text-gray-400">CPU Usage</span>
            <span className="text-gray-900 dark:text-white font-medium">{formatPercent(health?.cpu_percent ?? null)}</span>
          </div>
          <ProgressBar
            value={health?.cpu_percent ?? 0}
            color={health?.cpu_percent && health.cpu_percent > 80 ? 'red' : health?.cpu_percent && health.cpu_percent > 60 ? 'yellow' : 'blue'}
            showLabel={false}
          />
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-500 dark:text-gray-400">Memory Usage</span>
            <span className="text-gray-900 dark:text-white font-medium">{formatPercent(health?.memory_percent ?? null)}</span>
          </div>
          <ProgressBar
            value={health?.memory_percent ?? 0}
            color={health?.memory_percent && health.memory_percent > 80 ? 'red' : health?.memory_percent && health.memory_percent > 60 ? 'yellow' : 'green'}
            showLabel={false}
          />
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-500 dark:text-gray-400">Disk Usage</span>
            <span className="text-gray-900 dark:text-white font-medium">{formatPercent(health?.disk_percent ?? null)}</span>
          </div>
          <ProgressBar
            value={health?.disk_percent ?? 0}
            color={health?.disk_percent && health.disk_percent > 80 ? 'red' : health?.disk_percent && health.disk_percent > 60 ? 'yellow' : 'green'}
            showLabel={false}
          />
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Database</span>
            <span className={`font-medium ${health?.database === 'ok' ? 'text-green-600' : 'text-red-600'}`}>
              {health?.database?.toUpperCase() ?? 'N/A'}
            </span>
          </div>
          <div className="flex justify-between text-sm mt-2">
            <span className="text-gray-500 dark:text-gray-400">Last Updated</span>
            <span className="text-gray-900 dark:text-white font-medium text-xs">
              {formatDateTime(health?.timestamp ?? null)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
