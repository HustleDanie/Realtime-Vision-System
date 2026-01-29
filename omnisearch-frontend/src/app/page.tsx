import { MetricsOverview, HealthStatus, ModelStatusPanel, RecentInspections } from '@/components/dashboard';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Real-time monitoring of your AI vision inspection system
        </p>
      </div>

      {/* Metrics Overview */}
      <MetricsOverview />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Inspections - Takes 2 columns */}
        <div className="lg:col-span-2">
          <RecentInspections />
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          <HealthStatus />
          <ModelStatusPanel />
        </div>
      </div>
    </div>
  );
}
