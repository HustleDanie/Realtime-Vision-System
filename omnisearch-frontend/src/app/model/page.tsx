'use client';

import { useModelStatus, useMetrics, useHealth } from '@/lib/hooks';
import { formatDateTime, formatNumber, formatPercent, formatMs } from '@/lib/utils';
import { ProgressBar } from '@/components/ui';

export default function ModelPage() {
  const { data: model, loading: modelLoading, error: modelError } = useModelStatus();
  const { data: metrics, loading: metricsLoading } = useMetrics();
  const { data: health, loading: healthLoading } = useHealth();

  const isLoading = modelLoading || metricsLoading || healthLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Status</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Loading model information...</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 animate-pulse">
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
              <div className="space-y-3">
                {[...Array(4)].map((_, j) => (
                  <div key={j} className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (modelError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Status</h1>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-red-800 dark:text-red-400">
          Failed to load model status: {modelError}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Status</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Detailed information about your AI model and system performance
        </p>
      </div>

      {/* Model Info Card */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Model */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Active Model</h2>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
              <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
              RUNNING
            </span>
          </div>

          <div className="space-y-4">
            <div className="flex items-center p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-lg mr-4">
                <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Model Name</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{model?.model_name ?? 'N/A'}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">Version</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{model?.model_version ?? 'N/A'}</p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400">Last Prediction</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{formatDateTime(model?.last_prediction_time ?? null)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Stats */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Performance Statistics</h2>

          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">Total Predictions</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatNumber(model?.total_predictions ?? 0)}</span>
              </div>
              <ProgressBar value={100} color="blue" showLabel={false} />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">Defect Rate</span>
                <span className="font-semibold text-red-600">{formatPercent(metrics?.defect_rate ? metrics.defect_rate * 100 : 0)}</span>
              </div>
              <ProgressBar value={(metrics?.defect_rate ?? 0) * 100} color="red" showLabel={false} />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">Avg Confidence</span>
                <span className="font-semibold text-green-600">{formatPercent(metrics?.avg_confidence ? metrics.avg_confidence * 100 : null)}</span>
              </div>
              <ProgressBar value={(metrics?.avg_confidence ?? 0) * 100} color="green" showLabel={false} />
            </div>

            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Avg Inference Time</span>
                <span className="font-semibold text-purple-600">{formatMs(metrics?.avg_inference_time_ms ?? null)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* System Resources */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">System Resources</h2>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">CPU Usage</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatPercent(health?.cpu_percent ?? null)}</span>
              </div>
              <ProgressBar
                value={health?.cpu_percent ?? 0}
                color={health?.cpu_percent && health.cpu_percent > 80 ? 'red' : 'blue'}
                showLabel={false}
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">Memory Usage</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatPercent(health?.memory_percent ?? null)}</span>
              </div>
              <ProgressBar
                value={health?.memory_percent ?? 0}
                color={health?.memory_percent && health.memory_percent > 80 ? 'red' : 'green'}
                showLabel={false}
              />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500 dark:text-gray-400">Disk Usage</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatPercent(health?.disk_percent ?? null)}</span>
              </div>
              <ProgressBar
                value={health?.disk_percent ?? 0}
                color={health?.disk_percent && health.disk_percent > 80 ? 'red' : 'green'}
                showLabel={false}
              />
            </div>
          </div>
        </div>

        {/* Detection Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Detection Summary</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
              <p className="text-3xl font-bold text-green-600">{formatNumber((model?.total_predictions ?? 0) - (model?.defects_detected ?? 0))}</p>
              <p className="text-sm text-green-700 dark:text-green-400 mt-1">Passed</p>
            </div>
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-center">
              <p className="text-3xl font-bold text-red-600">{formatNumber(model?.defects_detected ?? 0)}</p>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">Defects</p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Success Rate</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">
                {formatPercent(model?.total_predictions ? ((model.total_predictions - (model.defects_detected ?? 0)) / model.total_predictions) * 100 : 100)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
