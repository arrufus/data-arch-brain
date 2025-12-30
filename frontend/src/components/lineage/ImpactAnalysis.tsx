'use client';

/**
 * Impact Analysis Component (Phase 7)
 *
 * Analyzes and displays the impact of schema changes on column lineage
 */

import { useState } from 'react';
import { useColumnImpact } from '@/lib/api/column-lineage';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Download,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';

interface ImpactAnalysisProps {
  columnUrn: string;
  defaultChangeType?: 'delete' | 'rename' | 'type_change';
}

export default function ImpactAnalysis({
  columnUrn,
  defaultChangeType = 'delete',
}: ImpactAnalysisProps) {
  const [changeType, setChangeType] = useState<'delete' | 'rename' | 'type_change'>(
    defaultChangeType
  );
  const [expandedChanges, setExpandedChanges] = useState<Set<number>>(new Set());

  const { data: impact, isLoading, error } = useColumnImpact(columnUrn, changeType);

  const toggleChange = (index: number) => {
    const newExpanded = new Set(expandedChanges);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedChanges(newExpanded);
  };

  const exportReport = () => {
    // TODO: Implement export functionality
    console.log('Exporting impact report...');
    alert('Export functionality coming soon!');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Analyzing impact...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-900 mb-1">Failed to analyze impact</h3>
            <p className="text-sm text-red-700">
              {error instanceof Error ? error.message : 'An unknown error occurred'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!impact) {
    return (
      <div className="p-6 text-center text-gray-600">
        <Info className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm">No impact data available</p>
      </div>
    );
  }

  const riskColor = getRiskColor(impact.risk_level);
  const riskIcon = getRiskIcon(impact.risk_level);

  return (
    <div className="space-y-6">
      {/* Change Type Selector */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-gray-700">Change Type:</label>
        <div className="flex gap-2">
          {(['delete', 'rename', 'type_change'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setChangeType(type)}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-colors
                ${
                  changeType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
              `}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Risk Level Banner */}
      <div className={`p-4 rounded-lg border-2 ${riskColor.bg} ${riskColor.border}`}>
        <div className="flex items-start gap-3">
          {riskIcon}
          <div className="flex-1">
            <h3 className={`text-lg font-semibold ${riskColor.text} mb-1`}>
              {impact.risk_level.toUpperCase()} Risk
            </h3>
            <p className={`text-sm ${riskColor.subtext}`}>
              This {changeType.replace('_', ' ')} will affect{' '}
              <strong>{impact.affected_columns}</strong> downstream column
              {impact.affected_columns !== 1 ? 's' : ''} across{' '}
              <strong>{impact.affected_capsules}</strong> capsule
              {impact.affected_capsules !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Impact Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <ImpactCard
          label="Affected Columns"
          value={impact.affected_columns}
          color="text-blue-600"
        />
        <ImpactCard
          label="Affected Capsules"
          value={impact.affected_capsules}
          color="text-purple-600"
        />
        <ImpactCard label="Affected Tasks" value={impact.affected_tasks} color="text-orange-600" />
      </div>

      {/* Breaking Changes */}
      {impact.breaking_changes.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900">
              Breaking Changes ({impact.breaking_changes.length})
            </h3>
            <p className="text-xs text-gray-600 mt-0.5">
              Dependencies that will break if you proceed with this change
            </p>
          </div>
          <div className="divide-y divide-gray-200">
            {impact.breaking_changes.map((change, index) => (
              <div key={index} className="p-4">
                <button
                  onClick={() => toggleChange(index)}
                  className="w-full flex items-start gap-3 text-left"
                >
                  <AlertTriangle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-medium text-gray-900 truncate">
                        {change.target_column_name}
                      </span>
                      {expandedChanges.has(index) ? (
                        <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      )}
                    </div>
                    <div className="text-sm text-gray-600 truncate">{change.capsule_name}</div>
                    {change.transformation_type && (
                      <div className="mt-1">
                        <TransformationBadge type={change.transformation_type} />
                      </div>
                    )}
                  </div>
                </button>
                {expandedChanges.has(index) && (
                  <div className="mt-3 ml-8 space-y-2">
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <div className="text-xs font-medium text-red-900 mb-1">Reason:</div>
                      <div className="text-sm text-red-700">{change.reason}</div>
                    </div>
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="text-xs font-medium text-blue-900 mb-1">
                        Suggested Action:
                      </div>
                      <div className="text-sm text-blue-700">{change.suggested_action}</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-600" />
          Recommendations
        </h3>
        <ul className="space-y-2">
          {impact.recommendations.map((rec, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
              <div className="w-1.5 h-1.5 rounded-full bg-green-600 mt-2 flex-shrink-0" />
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-4">
        <button
          onClick={exportReport}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export Report
        </button>
        <div className="flex-1" />
        <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
          Cancel
        </button>
        <button
          className={`
            px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2
            ${
              impact.risk_level === 'high' || impact.risk_level === 'medium'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }
          `}
        >
          {impact.risk_level === 'high' && <AlertTriangle className="w-4 h-4" />}
          Proceed with Change
        </button>
      </div>
    </div>
  );
}

// Helper Components

function ImpactCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg">
      <div className={`text-3xl font-bold ${color} mb-1`}>{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}

function TransformationBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    identity: 'bg-blue-100 text-blue-700',
    cast: 'bg-purple-100 text-purple-700',
    aggregate: 'bg-orange-100 text-orange-700',
    string_transform: 'bg-green-100 text-green-700',
    arithmetic: 'bg-yellow-100 text-yellow-700',
  };

  const colorClass = colors[type] || 'bg-gray-100 text-gray-700';

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {type.replace('_', ' ')}
    </span>
  );
}

// Helper Functions

function getRiskColor(riskLevel: string) {
  const colors = {
    none: {
      bg: 'bg-gray-50',
      border: 'border-gray-300',
      text: 'text-gray-900',
      subtext: 'text-gray-700',
    },
    low: {
      bg: 'bg-green-50',
      border: 'border-green-300',
      text: 'text-green-900',
      subtext: 'text-green-700',
    },
    medium: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-300',
      text: 'text-yellow-900',
      subtext: 'text-yellow-700',
    },
    high: {
      bg: 'bg-red-50',
      border: 'border-red-300',
      text: 'text-red-900',
      subtext: 'text-red-700',
    },
  };
  return colors[riskLevel as keyof typeof colors] || colors.none;
}

function getRiskIcon(riskLevel: string) {
  const iconClass = 'w-6 h-6 flex-shrink-0';
  switch (riskLevel) {
    case 'none':
      return <CheckCircle className={`${iconClass} text-gray-600`} />;
    case 'low':
      return <Info className={`${iconClass} text-green-600`} />;
    case 'medium':
      return <AlertTriangle className={`${iconClass} text-yellow-600`} />;
    case 'high':
      return <XCircle className={`${iconClass} text-red-600`} />;
    default:
      return <Info className={`${iconClass} text-gray-600`} />;
  }
}
