'use client';

/**
 * Columns Tab Component
 *
 * Displays all columns for a capsule with PII highlighting and filtering.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { ColumnSummary } from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { Search, Filter } from 'lucide-react';

interface ColumnsTabProps {
  capsuleUrn: string;
}

export default function ColumnsTab({ capsuleUrn }: ColumnsTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [piiFilter, setPiiFilter] = useState<'all' | 'pii-only' | 'no-pii'>('all');

  // Fetch columns for this capsule
  const { data: columnsData, isLoading, error, refetch } = useQuery({
    queryKey: ['capsule-columns', capsuleUrn],
    queryFn: async () => {
      const response = await apiClient.get<{ data: ColumnSummary[]; pagination: any }>(
        `/api/v1/capsules/${encodeURIComponent(capsuleUrn)}/columns`
      );
      return response.data;
    },
  });

  const columns = columnsData?.data || [];

  if (isLoading) {
    return <Loading text="Loading columns..." />;
  }

  if (error || !columnsData) {
    return (
      <ErrorMessage
        title="Failed to load columns"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  // Filter columns
  const filteredColumns = columns.filter((col) => {
    // Search filter
    if (searchQuery && !col.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    // PII filter
    if (piiFilter === 'pii-only' && !col.pii_type) {
      return false;
    }
    if (piiFilter === 'no-pii' && col.pii_type) {
      return false;
    }

    return true;
  });

  const piiCount = columns.filter((c) => c.pii_type).length;

  return (
    <div className="space-y-4">
      {/* Header Stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-2xl font-bold text-gray-900">{columns.length}</span>
            <span className="text-gray-600 ml-2">columns</span>
          </div>
          {piiCount > 0 && (
            <Badge variant="pii" size="md">
              {piiCount} PII
            </Badge>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* PII Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={piiFilter}
            onChange={(e) => setPiiFilter(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Columns</option>
            <option value="pii-only">PII Only</option>
            <option value="no-pii">No PII</option>
          </select>
        </div>
      </div>

      {/* Columns Table */}
      {filteredColumns.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No columns found matching your filters.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-y border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Position
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Semantic Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  PII Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Constraints
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredColumns.map((column) => (
                <tr key={column.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {column.ordinal_position}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <div className="font-medium text-gray-900">{column.name}</div>
                      {column.description && (
                        <div className="text-sm text-gray-500 max-w-md truncate">
                          {column.description}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Badge variant="default" size="sm">
                      {column.data_type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {column.semantic_type || '-'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {column.pii_type ? (
                      <Badge variant="pii" size="sm">
                        {column.pii_type}
                      </Badge>
                    ) : (
                      <span className="text-sm text-gray-400">None</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <div className="flex gap-1">
                      {!column.is_nullable && (
                        <Badge variant="default" size="sm">
                          NOT NULL
                        </Badge>
                      )}
                      {column.is_unique && (
                        <Badge variant="info" size="sm">
                          UNIQUE
                        </Badge>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Results Count */}
      {searchQuery || piiFilter !== 'all' ? (
        <div className="text-sm text-gray-600 text-center">
          Showing {filteredColumns.length} of {columns.length} columns
        </div>
      ) : null}
    </div>
  );
}
