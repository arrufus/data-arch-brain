'use client';

/**
 * Violations Tab Component
 *
 * Displays conformance violations for a capsule with filtering by severity.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { ConformanceViolation, ViolationFilters } from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { AlertTriangle, CheckCircle, Filter } from 'lucide-react';

interface ViolationsTabProps {
  capsuleUrn: string;
}

export default function ViolationsTab({ capsuleUrn }: ViolationsTabProps) {
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const filters: ViolationFilters = {
    capsule_urn: capsuleUrn,
    severity: severityFilter !== 'all' ? (severityFilter as any) : undefined,
    offset: 0,
    limit: 100,
  };

  // Fetch violations
  const { data: violationsData, isLoading, error, refetch } = useQuery({
    queryKey: ['capsule-violations', capsuleUrn, severityFilter],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/violations', {
        params: filters,
      });
      return response.data;
    },
  });

  if (isLoading) {
    return <Loading text="Loading violations..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load violations"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  const violations = violationsData?.data || [];
  const total = violationsData?.pagination?.total || 0;

  // Count by severity
  const criticalCount = violations.filter((v: ConformanceViolation) => v.severity === 'critical').length;
  const errorCount = violations.filter((v: ConformanceViolation) => v.severity === 'error').length;
  const warningCount = violations.filter((v: ConformanceViolation) => v.severity === 'warning').length;
  const infoCount = violations.filter((v: ConformanceViolation) => v.severity === 'info').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {total === 0 ? 'No violations found' : `${total} violation${total > 1 ? 's' : ''} found`}
          </h3>
          {total === 0 && (
            <p className="text-gray-600 mt-1">This capsule passes all conformance rules.</p>
          )}
        </div>

        {total > 0 && (
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
        )}
      </div>

      {/* No Violations - Success State */}
      {total === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <h4 className="text-lg font-semibold text-green-900 mb-2">
            All Conformance Rules Passed
          </h4>
          <p className="text-green-700">
            This capsule meets all architecture conformance standards.
          </p>
        </div>
      )}

      {/* Severity Stats */}
      {total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <SeverityCard label="Critical" count={criticalCount} variant="critical" />
          <SeverityCard label="Error" count={errorCount} variant="error" />
          <SeverityCard label="Warning" count={warningCount} variant="warning" />
          <SeverityCard label="Info" count={infoCount} variant="info" />
        </div>
      )}

      {/* Violations List */}
      {violations.length > 0 && (
        <div className="space-y-3">
          {violations.map((violation: ConformanceViolation) => (
            <ViolationCard key={violation.id} violation={violation} />
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

// Violation Card Component
function ViolationCard({ violation }: { violation: ConformanceViolation }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
          violation.severity === 'critical' ? 'text-red-600' :
          violation.severity === 'error' ? 'text-orange-600' :
          violation.severity === 'warning' ? 'text-yellow-600' :
          'text-blue-600'
        }`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={violation.severity} size="sm">
              {violation.severity}
            </Badge>
            <Badge variant="default" size="sm">
              {violation.rule_name}
            </Badge>
            <Badge variant={violation.status === 'open' ? 'error' : 'success'} size="sm">
              {violation.status}
            </Badge>
          </div>

          <p className="font-medium text-gray-900 mb-2">{violation.message}</p>

          {violation.remediation && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {isExpanded ? 'Hide' : 'Show'} remediation guidance
            </button>
          )}

          {isExpanded && violation.remediation && (
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-900 mb-1">Remediation:</p>
              <p className="text-sm text-blue-800">{violation.remediation}</p>
            </div>
          )}

          {violation.resolution_notes && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm font-medium text-green-900 mb-1">Resolution Notes:</p>
              <p className="text-sm text-green-800">{violation.resolution_notes}</p>
            </div>
          )}

          <div className="mt-3 text-xs text-gray-500">
            Detected: {new Date(violation.detected_at).toLocaleDateString()}
            {violation.acknowledged_at && (
              <> • Acknowledged by {violation.acknowledged_by} on {new Date(violation.acknowledged_at).toLocaleDateString()}</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
