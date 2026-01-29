'use client';

import { useModelStatus } from '@/lib/hooks';
import { formatDateTime, formatNumber } from '@/lib/utils';

export function ModelStatusPanel() {
  const { data: model, loading, error } = useModelStatus();

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Model Status</h3>
        <p className="text-red-600 dark:text-red-400">Failed to load: {error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Model Status</h3>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
          <span className="w-2 h-2 rounded-full bg-blue-500 mr-2 animate-pulse"></span>
          ACTIVE
        </span>
      </div>

      <div className="space-y-4">
        <div className="flex items-center p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg mr-3">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Model Name</p>
            <p className="font-semibold text-gray-900 dark:text-white">{model?.model_name ?? 'N/A'}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Version</p>
            <p className="font-semibold text-gray-900 dark:text-white">{model?.model_version ?? 'N/A'}</p>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Predictions</p>
            <p className="font-semibold text-gray-900 dark:text-white">{formatNumber(model?.total_predictions ?? 0)}</p>
          </div>
        </div>

        <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <p className="text-xs text-gray-500 dark:text-gray-400">Defects Detected</p>
          <p className="font-semibold text-red-600 dark:text-red-400">{formatNumber(model?.defects_detected ?? 0)}</p>
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">Last Prediction</p>
          <p className="text-sm text-gray-900 dark:text-white">{formatDateTime(model?.last_prediction_time ?? null)}</p>
        </div>
      </div>
    </div>
  );
}
