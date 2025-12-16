'use client';

/**
 * Capsules List Page
 *
 * Browse and search data capsules with filters and pagination.
 */

import { useState } from 'react';
import { useCapsules, useCapsuleStats } from '@/lib/api/capsules';
import { CapsuleFilters as CapsuleFiltersType } from '@/lib/api/types';
import CapsuleFilters from '@/components/capsules/CapsuleFilters';
import CapsuleTable from '@/components/capsules/CapsuleTable';
import Pagination from '@/components/common/Pagination';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import { Database, Layers, Shield } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

const DEFAULT_LIMIT = 20;

export default function CapsulesPage() {
  const [filters, setFilters] = useState<CapsuleFiltersType>({
    offset: 0,
    limit: DEFAULT_LIMIT,
  });

  // Fetch capsules with current filters
  const {
    data: capsulesData,
    isLoading: isLoadingCapsules,
    error: capsulesError,
    refetch: refetchCapsules,
  } = useCapsules(filters);

  // Fetch capsule stats
  const { data: statsData, isLoading: isLoadingStats } = useCapsuleStats();

  // Fetch PII stats from PII inventory endpoint (more accurate)
  const { data: piiData } = useQuery({
    queryKey: ['pii-inventory-summary'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/compliance/pii-inventory');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleFiltersChange = (newFilters: CapsuleFiltersType) => {
    setFilters(newFilters);
  };

  const handlePageChange = (newOffset: number) => {
    setFilters({ ...filters, offset: newOffset });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Data Capsules</h1>
        <p className="mt-2 text-gray-600">Browse and search your data assets</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Capsules"
          value={statsData?.total_capsules ?? 0}
          icon={<Database className="w-5 h-5" />}
          isLoading={isLoadingStats}
        />
        <StatCard
          label="Models"
          value={statsData?.by_type?.model ?? 0}
          icon={<Layers className="w-5 h-5" />}
          isLoading={isLoadingStats}
        />
        <StatCard
          label="With PII"
          value={piiData?.summary?.capsules_with_pii ?? 0}
          icon={<Shield className="w-5 h-5" />}
          isLoading={!piiData}
          badge={piiData?.summary?.capsules_with_pii ? 'pii' : undefined}
        />
        <StatCard
          label="Avg Columns"
          value={(statsData?.total_capsules && capsulesData?.data?.length
            ? (capsulesData.data.reduce((sum, c) => sum + c.column_count, 0) / capsulesData.data.length).toFixed(1)
            : '0')}
          icon={<Database className="w-5 h-5" />}
          isLoading={isLoadingStats}
        />
      </div>

      {/* Filters */}
      <CapsuleFilters filters={filters} onFiltersChange={handleFiltersChange} />

      {/* Loading State */}
      {isLoadingCapsules && (
        <div className="py-12">
          <Loading size="lg" text="Loading capsules..." />
        </div>
      )}

      {/* Error State */}
      {capsulesError && (
        <ErrorMessage
          title="Failed to load capsules"
          message={capsulesError.message}
          onRetry={refetchCapsules}
        />
      )}

      {/* Capsules Table */}
      {capsulesData && !isLoadingCapsules && (
        <>
          <CapsuleTable capsules={capsulesData.data} />

          {/* Pagination */}
          {capsulesData.pagination.total > 0 && (
            <Pagination
              total={capsulesData.pagination.total}
              offset={capsulesData.pagination.offset}
              limit={capsulesData.pagination.limit}
              onPageChange={handlePageChange}
            />
          )}
        </>
      )}

      {/* Empty State (when no filters but no data) */}
      {capsulesData?.data.length === 0 &&
        !filters.search &&
        !filters.layer &&
        !filters.capsule_type &&
        filters.has_pii === undefined && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No capsules yet</h3>
            <p className="text-gray-600 mb-4">
              Get started by ingesting metadata from your dbt project.
            </p>
            <a
              href="http://localhost:8002/api/v1/docs#/ingestion"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              View Ingestion Docs
            </a>
          </div>
        )}
    </div>
  );
}

// Stat Card Component
function StatCard({
  label,
  value,
  icon,
  isLoading,
  badge,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  isLoading: boolean;
  badge?: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">{label}</p>
          {isLoading ? (
            <div className="h-8 w-16 bg-gray-200 animate-pulse rounded mt-1" />
          ) : (
            <div className="flex items-center gap-2 mt-1">
              <p className="text-2xl font-bold text-gray-900">{value}</p>
              {badge && <Badge variant={badge as any} size="sm">{badge.toUpperCase()}</Badge>}
            </div>
          )}
        </div>
        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">{icon}</div>
      </div>
    </div>
  );
}
