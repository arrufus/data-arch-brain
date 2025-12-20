'use client';

/**
 * PII Inventory Tab Component
 *
 * Displays PII columns grouped by type and layer with charts.
 */

import { useState } from 'react';
import { usePIIInventory } from '@/lib/api/compliance';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Filter, Download } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';

const LAYER_COLORS = {
  raw: '#6B7280',
  bronze: '#D97706',
  silver: '#64748B',
  gold: '#EAB308',
  marts: '#8B5CF6',
  unknown: '#9CA3AF',
};

export default function PIIInventoryTab() {
  const [layerFilter, setLayerFilter] = useState<string>('all');
  const [piiTypeFilter, setPiiTypeFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = usePIIInventory(
    layerFilter !== 'all' ? layerFilter : undefined,
    piiTypeFilter !== 'all' ? piiTypeFilter : undefined
  );

  if (isLoading) {
    return <Loading text="Loading PII inventory..." />;
  }

  if (error || !data) {
    return (
      <ErrorMessage
        title="Failed to load PII inventory"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  // Prepare chart data
  const chartData = data.by_pii_type.map((item) => ({
    name: item.pii_type,
    count: item.column_count,
    capsules: item.capsule_count,
  }));

  const layerData = data.by_layer.map((item) => ({
    name: item.layer,
    count: item.column_count,
  }));

  const handleExport = () => {
    // Export as CSV
    const totalColumns = data.summary.total_pii_columns;
    const csv = [
      ['PII Type', 'Column Count', 'Capsule Count', 'Percentage'],
      ...data.by_pii_type.map((item) => [
        item.pii_type,
        item.column_count,
        item.capsule_count,
        `${((item.column_count / totalColumns) * 100).toFixed(1)}%`,
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pii-inventory-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Filters and Actions */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={layerFilter}
              onChange={(e) => setLayerFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Layers</option>
              <option value="raw">Raw</option>
              <option value="bronze">Bronze</option>
              <option value="silver">Silver</option>
              <option value="gold">Gold</option>
              <option value="marts">Marts</option>
            </select>
          </div>

          <select
            value={piiTypeFilter}
            onChange={(e) => setPiiTypeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All PII Types</option>
            {data.summary.pii_types_found.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* PII by Type Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">PII Columns by Type</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3B82F6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* PII by Layer Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">PII Distribution by Layer</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={layerData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={80} />
            <Tooltip />
            <Bar dataKey="count">
              {layerData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={LAYER_COLORS[entry.name as keyof typeof LAYER_COLORS] || LAYER_COLORS.unknown}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* PII Types Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                PII Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Column Count
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Capsule Count
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Percentage
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.by_pii_type.map((item) => {
              const percentage = (item.column_count / data.summary.total_pii_columns) * 100;
              return (
                <tr key={item.pii_type} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant="pii" size="sm">
                      {item.pii_type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.column_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.capsule_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {percentage.toFixed(1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
