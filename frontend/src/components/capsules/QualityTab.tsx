'use client';

/**
 * Quality Tab Component (Dimension 4)
 *
 * Displays quality rules and column profiles for a capsule.
 * Shows quality metrics including completeness, validity, and uniqueness scores.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import {
  QualityRule,
  ColumnProfile,
  QualitySummary,
  RuleSeverity,
  QualityRuleType,
} from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { Search, Filter, CheckCircle2, AlertCircle, Info, TrendingUp } from 'lucide-react';

interface QualityTabProps {
  capsuleUrn: string;
}

type QualityView = 'rules' | 'profiles';

export default function QualityTab({ capsuleUrn }: QualityTabProps) {
  const [view, setView] = useState<QualityView>('rules');
  const [searchQuery, setSearchQuery] = useState('');
  const [ruleTypeFilter, setRuleTypeFilter] = useState<QualityRuleType | 'all'>('all');
  const [severityFilter, setSeverityFilter] = useState<RuleSeverity | 'all'>('all');
  const [enabledFilter, setEnabledFilter] = useState<boolean | 'all'>('all');

  // Fetch quality rules
  const {
    data: rulesData,
    isLoading: rulesLoading,
    error: rulesError,
    refetch: refetchRules,
  } = useQuery({
    queryKey: ['quality-rules', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: QualityRule[]; pagination: any }>(
          `/api/v1/quality-rules?capsule_urn=${encodeURIComponent(capsuleUrn)}`
        );
        return response.data;
      } catch (error: any) {
        // Return empty data if endpoint doesn't exist yet
        if (error?.status === 404 || error?.status === 422) {
          return { data: [], pagination: { total: 0, offset: 0, limit: 0, has_more: false } };
        }
        throw error;
      }
    },
    retry: false,
    throwOnError: false,
  });

  // Fetch column profiles
  const {
    data: profilesData,
    isLoading: profilesLoading,
    error: profilesError,
    refetch: refetchProfiles,
  } = useQuery({
    queryKey: ['column-profiles', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: ColumnProfile[]; pagination: any }>(
          `/api/v1/column-profiles?capsule_urn=${encodeURIComponent(capsuleUrn)}`
        );
        return response.data;
      } catch (error: any) {
        // Return empty data if endpoint doesn't exist yet
        if (error?.status === 404 || error?.status === 422) {
          return { data: [], pagination: { total: 0, offset: 0, limit: 0, has_more: false } };
        }
        throw error;
      }
    },
    enabled: view === 'profiles',
    retry: false,
    throwOnError: false,
  });

  const rules = rulesData?.data || [];
  const profiles = profilesData?.data || [];

  const isLoading = rulesLoading || (view === 'profiles' && profilesLoading);
  const error = rulesError || (view === 'profiles' && profilesError);

  if (isLoading) {
    return <Loading text="Loading quality data..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load quality data"
        message={error?.message || 'Unknown error'}
        onRetry={view === 'rules' ? refetchRules : refetchProfiles}
      />
    );
  }

  // Calculate summary stats
  const enabledRules = rules.filter((r) => r.is_enabled);
  const disabledRules = rules.filter((r) => r.is_enabled === false);
  const avgQualityScore =
    profiles.length > 0
      ? profiles.reduce((sum, p) => sum + p.completeness_score, 0) / profiles.length
      : null;
  const lastProfiled =
    profiles.length > 0
      ? new Date(
          Math.max(...profiles.map((p) => new Date(p.profiled_at).getTime()))
        ).toLocaleString()
      : null;

  // Filter rules
  const filteredRules = rules.filter((rule) => {
    // Search filter
    if (searchQuery && !rule.rule_name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    // Rule type filter
    if (ruleTypeFilter !== 'all' && rule.rule_type !== ruleTypeFilter) {
      return false;
    }

    // Severity filter
    if (severityFilter !== 'all' && rule.severity !== severityFilter) {
      return false;
    }

    // Enabled filter
    if (enabledFilter !== 'all' && rule.is_enabled !== enabledFilter) {
      return false;
    }

    return true;
  });

  const getSeverityBadgeVariant = (severity: RuleSeverity) => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getSeverityIcon = (severity: RuleSeverity) => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="w-4 h-4" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4" />;
      case 'info':
        return <Info className="w-4 h-4" />;
      default:
        return <CheckCircle2 className="w-4 h-4" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Rules</p>
              <p className="text-2xl font-bold text-gray-900">{rules.length}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Enabled Rules</p>
              <p className="text-2xl font-bold text-green-600">{enabledRules.length}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Quality Score</p>
              <p className={`text-2xl font-bold ${avgQualityScore ? getScoreColor(avgQualityScore) : 'text-gray-400'}`}>
                {avgQualityScore ? `${avgQualityScore.toFixed(1)}%` : 'N/A'}
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-purple-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Last Profiled</p>
              <p className="text-xs font-medium text-gray-900">
                {lastProfiled || 'Never'}
              </p>
            </div>
            <Info className="w-8 h-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* View Selector */}
      <div className="flex items-center gap-2 border-b border-gray-200">
        <button
          onClick={() => setView('rules')}
          className={`px-4 py-2 font-medium transition-colors ${
            view === 'rules'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Quality Rules ({rules.length})
        </button>
        <button
          onClick={() => setView('profiles')}
          className={`px-4 py-2 font-medium transition-colors ${
            view === 'profiles'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Column Profiles ({profiles.length})
        </button>
      </div>

      {view === 'rules' && (
        <>
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />

              <select
                value={ruleTypeFilter}
                onChange={(e) => setRuleTypeFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Types</option>
                <option value="not_null">Not Null</option>
                <option value="unique">Unique</option>
                <option value="range_check">Range Check</option>
                <option value="pattern_check">Pattern Check</option>
                <option value="referential_integrity">Referential Integrity</option>
                <option value="freshness">Freshness</option>
                <option value="row_count">Row Count</option>
              </select>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Severities</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>

              <select
                value={String(enabledFilter)}
                onChange={(e) =>
                  setEnabledFilter(e.target.value === 'all' ? 'all' : e.target.value === 'true')
                }
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Status</option>
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
          </div>

          {/* Rules Table */}
          {filteredRules.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No quality rules found matching your filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-y border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Rule Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Severity
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Blocking
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredRules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{rule.rule_name}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge variant="default" size="sm">
                          {rule.rule_type}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          {getSeverityIcon(rule.severity)}
                          <Badge variant={getSeverityBadgeVariant(rule.severity)} size="sm">
                            {rule.severity}
                          </Badge>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {rule.rule_category || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {rule.is_enabled ? (
                          <Badge variant="success" size="sm">
                            Enabled
                          </Badge>
                        ) : (
                          <Badge variant="default" size="sm">
                            Disabled
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {rule.blocking ? (
                          <Badge variant="error" size="sm">
                            Blocking
                          </Badge>
                        ) : (
                          <span className="text-gray-400">No</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Results Count */}
          {searchQuery ||
          ruleTypeFilter !== 'all' ||
          severityFilter !== 'all' ||
          enabledFilter !== 'all' ? (
            <div className="text-sm text-gray-600 text-center">
              Showing {filteredRules.length} of {rules.length} rules
            </div>
          ) : null}
        </>
      )}

      {view === 'profiles' && (
        <>
          {/* Column Profiles Table */}
          {profiles.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No column profiles found.</p>
              <p className="text-sm text-gray-400 mt-2">
                Column profiles are created when data profiling runs are executed.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-y border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Column
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completeness
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Validity
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Uniqueness
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Row Count
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Distinct Count
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Profiled At
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {profiles.map((profile) => (
                    <tr key={profile.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">Column {profile.column_id.substring(0, 8)}...</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`font-medium ${getScoreColor(profile.completeness_score)}`}>
                          {profile.completeness_score.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {profile.validity_score !== null ? (
                          <span className={`font-medium ${getScoreColor(profile.validity_score)}`}>
                            {profile.validity_score.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {profile.uniqueness_score !== null ? (
                          <span className={`font-medium ${getScoreColor(profile.uniqueness_score)}`}>
                            {profile.uniqueness_score.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {profile.row_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {profile.distinct_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                        {new Date(profile.profiled_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
