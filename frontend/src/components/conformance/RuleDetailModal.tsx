'use client';

/**
 * Rule Detail Modal Component
 *
 * Displays detailed information about a conformance rule.
 */

import { X, Shield, AlertCircle, CheckCircle, Settings } from 'lucide-react';
import Badge from '@/components/common/Badge';

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

interface RuleDetailModalProps {
  rule: ConformanceRule;
  isOpen: boolean;
  onClose: () => void;
  onToggleEnabled?: (ruleId: string, enabled: boolean) => void;
  onTest?: (ruleId: string) => void;
}

export default function RuleDetailModal({
  rule,
  isOpen,
  onClose,
  onToggleEnabled,
  onTest,
}: RuleDetailModalProps) {
  if (!isOpen) return null;

  const isBuiltIn = rule.rule_set !== 'custom';

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full">
          {/* Header */}
          <div className="flex items-start justify-between p-6 border-b border-gray-200">
            <div className="flex items-start gap-4 flex-1">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                <Shield className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{rule.name}</h2>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant={getSeverityVariant(rule.severity)} size="md">
                    {rule.severity}
                  </Badge>
                  <Badge variant="default" size="md">
                    {formatCategory(rule.category)}
                  </Badge>
                  {rule.rule_set && (
                    <Badge variant={isBuiltIn ? 'default' : 'info'} size="md">
                      {isBuiltIn ? 'Built-in' : 'Custom'}
                    </Badge>
                  )}
                  <Badge variant={rule.enabled ? 'success' : 'default'} size="md">
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Rule ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule ID
              </label>
              <code className="block px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm text-gray-900">
                {rule.rule_id}
              </code>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <p className="text-gray-900 leading-relaxed">{rule.description}</p>
            </div>

            {/* Rule Details Grid */}
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Severity
                </label>
                <div className="flex items-center gap-2">
                  {getSeverityIcon(rule.severity)}
                  <span className="text-gray-900 font-medium capitalize">
                    {rule.severity}
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category
                </label>
                <p className="text-gray-900 font-medium">{formatCategory(rule.category)}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scope
                </label>
                <p className="text-gray-900 font-medium capitalize">{rule.scope}</p>
              </div>

              {rule.rule_set && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Rule Set
                  </label>
                  <p className="text-gray-900 font-medium">{formatRuleSet(rule.rule_set)}</p>
                </div>
              )}
            </div>

            {/* Pattern */}
            {rule.pattern && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pattern
                </label>
                <code className="block px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm text-gray-900 overflow-x-auto">
                  {rule.pattern}
                </code>
              </div>
            )}

            {/* Remediation */}
            {rule.remediation && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-blue-600" />
                  Recommended Action
                </label>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-gray-900">{rule.remediation}</p>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center gap-4">
              {onToggleEnabled && (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={(e) => onToggleEnabled(rule.rule_id, e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  <span className="ml-3 text-sm font-medium text-gray-900">
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </label>
              )}
            </div>

            <div className="flex items-center gap-3">
              {onTest && (
                <button
                  onClick={() => onTest(rule.rule_id)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
                >
                  <CheckCircle className="w-4 h-4" />
                  Test Rule
                </button>
              )}
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
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

function getSeverityIcon(severity: string) {
  switch (severity) {
    case 'critical':
      return <AlertCircle className="w-5 h-5 text-red-600" />;
    case 'error':
      return <AlertCircle className="w-5 h-5 text-red-600" />;
    case 'warning':
      return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    case 'info':
      return <AlertCircle className="w-5 h-5 text-blue-600" />;
    default:
      return <Shield className="w-5 h-5 text-gray-600" />;
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
