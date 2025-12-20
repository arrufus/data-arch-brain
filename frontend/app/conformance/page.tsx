'use client';

/**
 * Conformance Dashboard Page
 *
 * Real-time conformance scoring, rule management, and violation tracking.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Shield, AlertTriangle, CheckCircle2, XCircle, TrendingUp, Settings } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';

// Tabs for different sections
type TabType = 'overview' | 'violations' | 'rules';

export default function ConformancePage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);

  // Fetch conformance score
  const { data: scoreData, isLoading: isLoadingScore, error: scoreError, refetch: refetchScore } = useQuery({
    queryKey: ['conformance-score'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/conformance/score');
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  });

  // Fetch violations
  const { data: violationsData, isLoading: isLoadingViolations, refetch: refetchViolations } = useQuery({
    queryKey: ['conformance-violations', selectedCategory, selectedSeverity],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/conformance/violations', {
        params: {
          category: selectedCategory || undefined,
          severity: selectedSeverity || undefined,
          limit: 100,
        },
      });
      return response.data;
    },
    enabled: activeTab === 'violations',
  });

  // Fetch rules
  const { data: rulesData, isLoading: isLoadingRules, refetch: refetchRules } = useQuery({
    queryKey: ['conformance-rules'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/conformance/rules');
      return response.data;
    },
    enabled: activeTab === 'rules',
  });

  if (isLoadingScore) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading text="Loading conformance data..." />
      </div>
    );
  }

  if (scoreError) {
    return (
      <div className="p-6">
        <ErrorMessage
          title="Failed to load conformance data"
          message={scoreError?.message || 'Unknown error'}
          onRetry={refetchScore}
        />
      </div>
    );
  }

  const score = scoreData?.score || 0;
  const weightedScore = scoreData?.weighted_score || 0;
  const summary = scoreData?.summary;
  const bySeverity = scoreData?.by_severity || {};
  const byCategory = scoreData?.by_category || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-600" />
          Conformance Dashboard
        </h1>
        <p className="mt-2 text-gray-600">
          Monitor architecture conformance, manage rules, and track violations
        </p>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Overall Score */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Overall Score</span>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold ${score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
              {score.toFixed(1)}%
            </span>
            <span className="text-sm text-gray-500">/ 100</span>
          </div>
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${score >= 80 ? 'bg-green-600' : score >= 60 ? 'bg-yellow-600' : 'bg-red-600'}`}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
        </div>

        {/* Weighted Score */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Weighted Score</span>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold ${weightedScore >= 80 ? 'text-green-600' : weightedScore >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
              {weightedScore.toFixed(1)}%
            </span>
            <span className="text-sm text-gray-500">/ 100</span>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Severity-weighted score
          </p>
        </div>

        {/* Passing Rules */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Passing Rules</span>
            <CheckCircle2 className="w-4 h-4 text-green-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-green-600">
              {summary?.passing_rules || 0}
            </span>
            <span className="text-sm text-gray-500">/ {summary?.total_rules || 0}</span>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {summary?.total_rules > 0 ? ((summary?.passing_rules / summary?.total_rules) * 100).toFixed(0) : 0}% compliance
          </p>
        </div>

        {/* Failing Rules */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Failing Rules</span>
            <XCircle className="w-4 h-4 text-red-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-red-600">
              {summary?.failing_rules || 0}
            </span>
            <span className="text-sm text-gray-500">violations</span>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Requires attention
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'overview'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('violations')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'violations'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Violations ({summary?.failing_rules || 0})
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'rules'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Rules Management
              </span>
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <OverviewTab
              bySeverity={bySeverity}
              byCategory={byCategory}
              onCategoryClick={(category) => {
                setSelectedCategory(category);
                setActiveTab('violations');
              }}
            />
          )}

          {/* Violations Tab */}
          {activeTab === 'violations' && (
            <ViolationsTab
              violations={violationsData?.data || []}
              isLoading={isLoadingViolations}
              selectedCategory={selectedCategory}
              selectedSeverity={selectedSeverity}
              onCategoryChange={setSelectedCategory}
              onSeverityChange={setSelectedSeverity}
              onRefresh={refetchViolations}
            />
          )}

          {/* Rules Tab */}
          {activeTab === 'rules' && (
            <RulesTab
              rules={rulesData?.data || []}
              ruleSets={rulesData?.rule_sets || []}
              isLoading={isLoadingRules}
              onRefresh={refetchRules}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// Overview Tab Component
function OverviewTab({
  bySeverity,
  byCategory,
  onCategoryClick,
}: {
  bySeverity: any;
  byCategory: any;
  onCategoryClick: (category: string) => void;
}) {
  const severityOrder = ['critical', 'error', 'warning', 'info'];
  const severityColors = {
    critical: { bg: 'bg-red-100', text: 'text-red-800', icon: 'text-red-600' },
    error: { bg: 'bg-orange-100', text: 'text-orange-800', icon: 'text-orange-600' },
    warning: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: 'text-yellow-600' },
    info: { bg: 'bg-blue-100', text: 'text-blue-800', icon: 'text-blue-600' },
  };

  return (
    <div className="space-y-6">
      {/* By Severity */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Breakdown by Severity</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {severityOrder.map((severity) => {
            const data = bySeverity[severity];
            if (!data) return null;

            const colors = severityColors[severity as keyof typeof severityColors];
            const passRate = data.total > 0 ? ((data.passing / data.total) * 100).toFixed(0) : 0;

            return (
              <div key={severity} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-medium capitalize ${colors.text}`}>
                    {severity}
                  </span>
                  <AlertTriangle className={`w-4 h-4 ${colors.icon}`} />
                </div>
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-2xl font-bold text-gray-900">
                    {data.failing}
                  </span>
                  <span className="text-sm text-gray-500">/ {data.total}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${colors.bg}`}
                      style={{ width: `${100 - Number(passRate)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600">{passRate}% pass</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* By Category */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Breakdown by Category</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(byCategory).map(([category, data]: [string, any]) => {
            const passRate = data.total > 0 ? ((data.pass / data.total) * 100).toFixed(0) : 0;

            return (
              <button
                key={category}
                onClick={() => onCategoryClick(category)}
                className="bg-white border border-gray-200 rounded-lg p-4 text-left hover:border-blue-300 hover:shadow-md transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium capitalize text-gray-700">
                    {category.replace(/_/g, ' ')}
                  </span>
                  <span className={`text-lg font-bold ${data.fail > 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {data.fail}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${data.fail > 0 ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${100 - Number(passRate)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600">{passRate}%</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  {data.pass} passing, {data.fail} failing
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Violations Tab Component
function ViolationsTab({
  violations,
  isLoading,
  selectedCategory,
  selectedSeverity,
  onCategoryChange,
  onSeverityChange,
  onRefresh,
}: {
  violations: any[];
  isLoading: boolean;
  selectedCategory: string | null;
  selectedSeverity: string | null;
  onCategoryChange: (category: string | null) => void;
  onSeverityChange: (severity: string | null) => void;
  onRefresh: () => void;
}) {
  const severityColors = {
    critical: 'bg-red-100 text-red-800',
    error: 'bg-orange-100 text-orange-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
  };

  if (isLoading) {
    return <Loading text="Loading violations..." />;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
          <select
            value={selectedSeverity || ''}
            onChange={(e) => onSeverityChange(e.target.value || null)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select
            value={selectedCategory || ''}
            onChange={(e) => onCategoryChange(e.target.value || null)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Categories</option>
            <option value="naming">Naming</option>
            <option value="structure">Structure</option>
            <option value="documentation">Documentation</option>
            <option value="testing">Testing</option>
            <option value="ownership">Ownership</option>
          </select>
        </div>

        {(selectedCategory || selectedSeverity) && (
          <button
            onClick={() => {
              onCategoryChange(null);
              onSeverityChange(null);
            }}
            className="mt-6 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Clear Filters
          </button>
        )}

        <button
          onClick={onRefresh}
          className="mt-6 ml-auto px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Violations List */}
      {violations.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <p className="text-gray-600">No violations found</p>
          <p className="text-sm text-gray-500 mt-1">All rules are passing for the selected filters</p>
        </div>
      ) : (
        <div className="space-y-3">
          {violations.map((violation, idx) => (
            <div
              key={idx}
              className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start gap-4">
                <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  violation.severity === 'critical' ? 'text-red-600' :
                  violation.severity === 'error' ? 'text-orange-600' :
                  violation.severity === 'warning' ? 'text-yellow-600' :
                  'text-blue-600'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <h4 className="font-semibold text-gray-900">{violation.rule_name}</h4>
                      <p className="text-sm text-gray-600 mt-1">{violation.message}</p>
                    </div>
                    <div className="flex gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${severityColors[violation.severity as keyof typeof severityColors]}`}>
                        {violation.severity}
                      </span>
                      <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700 capitalize">
                        {violation.category.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>

                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Subject:</strong> {violation.subject_name}</p>
                    <p className="font-mono text-xs text-gray-500">{violation.subject_urn}</p>
                  </div>

                  {violation.remediation && (
                    <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                      <p className="text-sm font-medium text-blue-900 mb-1">Remediation:</p>
                      <p className="text-sm text-blue-800">{violation.remediation}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Rules Tab Component
function RulesTab({
  rules,
  ruleSets,
  isLoading,
  onRefresh,
}: {
  rules: any[];
  ruleSets: string[];
  isLoading: boolean;
  onRefresh: () => void;
}) {
  const [selectedRuleSet, setSelectedRuleSet] = useState<string | null>(null);

  if (isLoading) {
    return <Loading text="Loading rules..." />;
  }

  const filteredRules = selectedRuleSet
    ? rules.filter((r) => r.rule_set === selectedRuleSet)
    : rules;

  return (
    <div className="space-y-4">
      {/* Rule Set Filter */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Set</label>
            <select
              value={selectedRuleSet || ''}
              onChange={(e) => setSelectedRuleSet(e.target.value || null)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Rule Sets</option>
              {ruleSets.map((ruleSet) => (
                <option key={ruleSet} value={ruleSet}>
                  {ruleSet}
                </option>
              ))}
            </select>
          </div>

          {selectedRuleSet && (
            <button
              onClick={() => setSelectedRuleSet(null)}
              className="mt-6 text-sm text-gray-600 hover:text-gray-900"
            >
              Clear Filter
            </button>
          )}
        </div>

        <button
          onClick={onRefresh}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh Rules
        </button>
      </div>

      {/* Rules Count */}
      <p className="text-sm text-gray-600">
        Showing {filteredRules.length} rule{filteredRules.length !== 1 ? 's' : ''}
        {selectedRuleSet && ` from ${selectedRuleSet}`}
      </p>

      {/* Rules List */}
      <div className="space-y-3">
        {filteredRules.map((rule) => (
          <div
            key={rule.rule_id}
            className="border border-gray-200 rounded-lg p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h4 className="font-semibold text-gray-900">{rule.name}</h4>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    rule.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    rule.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                    rule.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {rule.severity}
                  </span>
                  <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700 capitalize">
                    {rule.category.replace(/_/g, ' ')}
                  </span>
                  {rule.enabled ? (
                    <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                      Enabled
                    </span>
                  ) : (
                    <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
                      Disabled
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                <div className="text-xs text-gray-500 space-y-1">
                  <p><strong>Rule ID:</strong> {rule.rule_id}</p>
                  <p><strong>Scope:</strong> {rule.scope}</p>
                  {rule.rule_set && <p><strong>Rule Set:</strong> {rule.rule_set}</p>}
                  {rule.pattern && <p><strong>Pattern:</strong> <code className="font-mono">{rule.pattern}</code></p>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Info Note */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> Rule management UI is read-only in this version.
          Use the API or CLI to add, modify, or delete custom rules.
        </p>
      </div>
    </div>
  );
}
