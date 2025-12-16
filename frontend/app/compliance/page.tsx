'use client';

/**
 * Compliance Dashboard Page
 *
 * PII compliance monitoring with inventory, exposure detection, and tracing.
 */

import { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Search } from 'lucide-react';
import { usePIIInventory, usePIIExposure } from '@/lib/api/compliance';
import PIIInventoryTab from '@/components/compliance/PIIInventoryTab';
import PIIExposureTab from '@/components/compliance/PIIExposureTab';
import PIITraceTab from '@/components/compliance/PIITraceTab';
import { LoadingSkeleton } from '@/components/common/Loading';

type TabType = 'inventory' | 'exposure' | 'trace';

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<TabType>('inventory');

  // Fetch summary data
  const { data: inventoryData, isLoading: isLoadingInventory } = usePIIInventory();
  const { data: exposureData, isLoading: isLoadingExposure } = usePIIExposure();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">PII Compliance</h1>
        <p className="mt-2 text-gray-600">
          Monitor and track personally identifiable information across your data assets
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total PII Columns"
          value={inventoryData?.summary?.total_pii_columns}
          icon={<Shield className="w-5 h-5" />}
          color="blue"
          isLoading={isLoadingInventory}
        />
        <StatCard
          label="Capsules with PII"
          value={inventoryData?.summary?.capsules_with_pii}
          icon={<Shield className="w-5 h-5" />}
          color="purple"
          isLoading={isLoadingInventory}
        />
        <StatCard
          label="PII Types Found"
          value={inventoryData?.summary?.pii_types_found?.length}
          icon={<CheckCircle className="w-5 h-5" />}
          color="green"
          isLoading={isLoadingInventory}
        />
        <StatCard
          label="Exposed PII"
          value={exposureData?.summary?.exposed_pii_columns}
          icon={<AlertTriangle className="w-5 h-5" />}
          color="red"
          isLoading={isLoadingExposure}
        />
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-8 px-6" aria-label="Tabs">
            <TabButton
              active={activeTab === 'inventory'}
              onClick={() => setActiveTab('inventory')}
              icon={<Shield className="w-4 h-4" />}
            >
              PII Inventory
            </TabButton>
            <TabButton
              active={activeTab === 'exposure'}
              onClick={() => setActiveTab('exposure')}
              icon={<AlertTriangle className="w-4 h-4" />}
              badge={exposureData?.summary?.exposed_pii_columns}
            >
              Exposure Detection
            </TabButton>
            <TabButton
              active={activeTab === 'trace'}
              onClick={() => setActiveTab('trace')}
              icon={<Search className="w-4 h-4" />}
            >
              PII Trace
            </TabButton>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'inventory' && <PIIInventoryTab />}
          {activeTab === 'exposure' && <PIIExposureTab />}
          {activeTab === 'trace' && <PIITraceTab />}
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({
  label,
  value,
  icon,
  color,
  isLoading,
}: {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  color: 'blue' | 'purple' | 'green' | 'red';
  isLoading: boolean;
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">{label}</p>
          {isLoading ? (
            <LoadingSkeleton className="h-8 w-16 mt-1" />
          ) : (
            <p className="text-2xl font-bold text-gray-900 mt-1">{value ?? 0}</p>
          )}
        </div>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  );
}

// Tab Button Component
function TabButton({
  active,
  onClick,
  children,
  icon,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  icon?: React.ReactNode;
  badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        py-4 border-b-2 font-medium text-sm transition-colors flex items-center gap-2
        ${
          active
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }
      `}
    >
      {icon}
      {children}
      {badge !== undefined && badge > 0 && (
        <span
          className={`
            px-2 py-0.5 rounded-full text-xs font-medium
            ${active ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}
          `}
        >
          {badge}
        </span>
      )}
    </button>
  );
}
