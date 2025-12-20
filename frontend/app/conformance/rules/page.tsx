'use client';

/**
 * Rules Management Page
 *
 * Comprehensive interface for managing conformance rules with CRUD operations.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import {
  Search,
  Filter,
  Plus,
  Upload,
  Download,
  PlayCircle,
  Shield,
  AlertCircle,
  CheckCircle,
  XCircle,
  Settings,
} from 'lucide-react';

interface ConformanceRule {
  rule_id: string;
  name: string;
  description: string;
  severity: string;
  category: string;
  rule_set: string | null;
  scope: string;
  enabled: boolean;
  pattern: string | null;
  remediation: string | null;
}

type RuleSeverity = 'critical' | 'error' | 'warning' | 'info';
type RuleCategory = string;
type RuleScope = 'capsule' | 'column' | 'domain' | 'global';

export default function RulesManagementPage() {
  const queryClient = useQueryClient();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRuleSet, setSelectedRuleSet] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<RuleSeverity | 'all'>('all');
  const [selectedScope, setSelectedScope] = useState<RuleScope | 'all'>('all');
  const [enabledFilter, setEnabledFilter] = useState<'all' | 'enabled' | 'disabled'>('all');

  // Fetch rules
  const {
    data: rulesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['conformance-rules'],
    queryFn: async () => {
      const response = await apiClient.get<{ data: ConformanceRule[]; rule_sets: string[] }>(
        '/api/v1/conformance/rules?enabled=false'
      );
      return response.data;
    },
  });

  const rules = rulesData?.data || [];
  const ruleSets = rulesData?.rule_sets || [];

  // Calculate statistics
  const stats = {
    total: rules.length,
    builtin: rules.filter((r) => r.rule_set !== 'custom').length,
    custom: rules.filter((r) => r.rule_set === 'custom').length,
    enabled: rules.filter((r) => r.enabled).length,
    disabled: rules.filter((r) => !r.enabled).length,
  };

  // Apply filters
  const filteredRules = rules.filter((rule) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        rule.name.toLowerCase().includes(query) ||
        rule.description.toLowerCase().includes(query) ||
        rule.rule_id.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }

    // Rule set filter
    if (selectedRuleSet !== 'all' && rule.rule_set !== selectedRuleSet) {
      return false;
    }

    // Category filter
    if (selectedCategory !== 'all' && rule.category !== selectedCategory) {
      return false;
    }

    // Severity filter
    if (selectedSeverity !== 'all' && rule.severity !== selectedSeverity) {
      return false;
    }

    // Scope filter
    if (selectedScope !== 'all' && rule.scope !== selectedScope) {
      return false;
    }

    // Enabled filter
    if (enabledFilter === 'enabled' && !rule.enabled) {
      return false;
    }
    if (enabledFilter === 'disabled' && rule.enabled) {
      return false;
    }

    return true;
  });

  // Get unique categories
  const categories = Array.from(new Set(rules.map((r) => r.category)));

  if (isLoading) {
    return (
      <div className="py-12">
        <Loading size="lg" text="Loading conformance rules..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load rules"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Conformance Rules</h1>
          <p className="text-gray-600 mt-1">
            Manage and configure data governance rules for your architecture
          </p>
        </div>
      </div>

      {/* Stats Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Total Rules</p>
            <Shield className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Built-in</p>
            <CheckCircle className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.builtin}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Custom</p>
            <Settings className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.custom}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Enabled</p>
            <CheckCircle className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.enabled}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Disabled</p>
            <XCircle className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.disabled}</p>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors">
            <Plus className="w-4 h-4" />
            Create Rule
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors">
            <Upload className="w-4 h-4" />
            Import YAML
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors">
            <Download className="w-4 h-4" />
            Export YAML
          </button>
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors">
          <PlayCircle className="w-4 h-4" />
          Test All Rules
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
          {/* Search */}
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Rule Set */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Rule Set</label>
            <select
              value={selectedRuleSet}
              onChange={(e) => setSelectedRuleSet(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Sets</option>
              {ruleSets.map((set) => (
                <option key={set} value={set}>
                  {formatRuleSet(set)}
                </option>
              ))}
            </select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {formatCategory(cat)}
                </option>
              ))}
            </select>
          </div>

          {/* Severity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Severity</label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              value={enabledFilter}
              onChange={(e) => setEnabledFilter(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Rules</option>
              <option value="enabled">Enabled Only</option>
              <option value="disabled">Disabled Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Rules List */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Rules ({filteredRules.length})
          </h2>
        </div>

        {filteredRules.length === 0 ? (
          <div className="text-center py-12">
            <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 text-lg mb-2">No rules found</p>
            <p className="text-gray-500 text-sm">
              Try adjusting your filters or create a new rule
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredRules.map((rule) => (
              <div
                key={rule.rule_id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0 pr-4">
                    {/* Rule Header */}
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">{rule.name}</h3>
                      <Badge variant={getSeverityVariant(rule.severity)} size="sm">
                        {rule.severity}
                      </Badge>
                      <Badge variant="default" size="sm">
                        {formatCategory(rule.category)}
                      </Badge>
                      {rule.rule_set && (
                        <Badge
                          variant={rule.rule_set === 'custom' ? 'info' : 'default'}
                          size="sm"
                        >
                          {rule.rule_set === 'custom' ? 'Custom' : 'Built-in'}
                        </Badge>
                      )}
                    </div>

                    {/* Rule Description */}
                    <p className="text-sm text-gray-600 mb-3">{rule.description}</p>

                    {/* Rule Details */}
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="font-mono">{rule.rule_id}</span>
                      <span>Scope: {rule.scope}</span>
                      {rule.rule_set && (
                        <span>Set: {formatRuleSet(rule.rule_set)}</span>
                      )}
                    </div>

                    {/* Remediation */}
                    {rule.remediation && (
                      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-xs text-blue-600 mb-1 font-medium">
                          Recommended Action
                        </p>
                        <p className="text-sm text-gray-700">{rule.remediation}</p>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={rule.enabled}
                        onChange={() => {}}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      <span className="ml-3 text-sm font-medium text-gray-900">
                        {rule.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper Functions

function getSeverityVariant(
  severity: string
): 'danger' | 'warning' | 'info' | 'default' {
  switch (severity) {
    case 'critical':
      return 'danger';
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'default';
  }
}

function formatRuleSet(ruleSet: string): string {
  return ruleSet
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatCategory(category: string): string {
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
