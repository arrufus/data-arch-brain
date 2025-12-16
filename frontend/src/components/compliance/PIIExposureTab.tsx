'use client';

/**
 * PII Exposure Tab Component
 *
 * Displays unmasked PII in consumption layers with severity indicators.
 */

import { useState } from 'react';
import { usePIIExposure } from '@/lib/api/compliance';
import { AlertTriangle, Filter, ShieldAlert } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import Link from 'next/link';

export default function PIIExposureTab() {
  const [layerFilter, setLayerFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = usePIIExposure(
    layerFilter !== 'all' ? layerFilter : undefined,
    severityFilter !== 'all' ? severityFilter : undefined
  );

  if (isLoading) {
    return <Loading text="Loading PII exposure data..." />;
  }

  if (error || !data) {
    return (
      <ErrorMessage
        title="Failed to load PII exposure"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  const { summary, exposures } = data;

  return (
    <div className="space-y-6">
      {/* Warning Banner */}
      {summary.exposed_pii_columns > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <ShieldAlert className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900">PII Exposure Detected</h3>
            <p className="text-sm text-red-700 mt-1">
              Found {summary.exposed_pii_columns} unmasked PII column{summary.exposed_pii_columns !== 1 ? 's' : ''} in
              consumption layers. These should be masked or protected to comply with data privacy regulations.
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={layerFilter}
            onChange={(e) => setLayerFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Layers</option>
            <option value="gold">Gold</option>
            <option value="marts">Marts</option>
          </select>
        </div>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Severity Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <SeverityCard label="Critical" count={summary.severity_breakdown?.critical || 0} variant="critical" />
        <SeverityCard label="High" count={summary.severity_breakdown?.high || 0} variant="error" />
        <SeverityCard label="Medium" count={summary.severity_breakdown?.medium || 0} variant="warning" />
        <SeverityCard label="Low" count={summary.severity_breakdown?.low || 0} variant="info" />
      </div>

      {/* No Exposures - Success State */}
      {exposures.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <AlertTriangle className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="text-lg font-semibold text-green-900 mb-2">No PII Exposure Detected</h4>
          <p className="text-green-700">
            All PII columns in consumption layers are properly masked or protected.
          </p>
        </div>
      )}

      {/* Exposures List */}
      {exposures.length > 0 && (
        <div className="space-y-3">
          {exposures.map((exposure, index) => (
            <ExposureCard key={`${exposure.column_urn}-${index}`} exposure={exposure} />
          ))}
        </div>
      )}
    </div>
  );
}

// Severity Card Component
function SeverityCard({
  label,
  count,
  variant,
}: {
  label: string;
  count: number;
  variant: 'critical' | 'error' | 'warning' | 'info';
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        <Badge variant={variant} size="sm">
          {label}
        </Badge>
      </div>
      <p className="text-2xl font-bold text-gray-900">{count}</p>
    </div>
  );
}

// Exposure Card Component
function ExposureCard({ exposure }: { exposure: any }) {
  const severityColors = {
    critical: 'text-red-600 bg-red-50 border-red-200',
    high: 'text-orange-600 bg-orange-50 border-orange-200',
    medium: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    low: 'text-blue-600 bg-blue-50 border-blue-200',
  };

  const severityColor = severityColors[exposure.severity as keyof typeof severityColors];

  return (
    <div className={`border rounded-lg p-4 ${severityColor}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${severityColor.split(' ')[0]}`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={exposure.severity} size="sm">
              {exposure.severity}
            </Badge>
            <Badge variant="pii" size="sm">
              {exposure.pii_type}
            </Badge>
            <Badge variant={exposure.layer as any} size="sm">
              {exposure.layer}
            </Badge>
          </div>

          <div className="mb-2">
            <Link
              href={`/capsules/${encodeURIComponent(exposure.capsule_urn)}`}
              className="font-medium hover:underline"
            >
              {exposure.capsule_name}
            </Link>
            <span className="text-sm mx-2">→</span>
            <span className="font-medium">{exposure.column_name}</span>
          </div>

          <p className="text-sm mb-2">{exposure.recommendation}</p>

          <div className="text-xs">
            <span className="font-mono">{exposure.column_urn}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
