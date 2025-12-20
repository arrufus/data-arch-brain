'use client';

/**
 * Rule Test Panel Component
 *
 * Test conformance rules against specific capsules and view results.
 */

import { useState } from 'react';
import { X, PlayCircle, CheckCircle, XCircle, AlertTriangle, Loader } from 'lucide-react';
import Badge from '@/components/common/Badge';

interface TestResult {
  score: number;
  weighted_score: number;
  summary: {
    total_rules: number;
    passing_rules: number;
    failing_rules: number;
    not_applicable: number;
  };
  by_severity: Record<string, { total: number; passing: number; failing: number }>;
  by_category: Record<string, { total: number; pass: number; fail: number }>;
  violation_count: number;
  violations: Array<{
    rule_id: string;
    rule_name: string;
    severity: string;
    category: string;
    subject_type: string;
    subject_urn: string;
    subject_name: string;
    message: string;
    details: Record<string, any>;
    remediation?: string;
  }>;
  computed_at: string;
}

interface RuleTestPanelProps {
  isOpen: boolean;
  onClose: () => void;
  ruleId?: string;
  ruleName?: string;
  onTest: (ruleId: string, capsuleUrns?: string[]) => Promise<TestResult>;
}

export default function RuleTestPanel({
  isOpen,
  onClose,
  ruleId,
  ruleName,
  onTest,
}: RuleTestPanelProps) {
  const [capsuleUrns, setCapsuleUrns] = useState<string>('');
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    if (!ruleId) {
      setError('No rule selected');
      return;
    }

    setIsTesting(true);
    setError(null);
    setTestResult(null);

    try {
      const urns = capsuleUrns
        .split('\n')
        .map((urn) => urn.trim())
        .filter((urn) => urn.length > 0);

      const result = await onTest(ruleId, urns.length > 0 ? urns : undefined);
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test rule');
    } finally {
      setIsTesting(false);
    }
  };

  const handleClose = () => {
    setCapsuleUrns('');
    setTestResult(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Panel */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Test Rule</h2>
                {ruleName && (
                  <p className="text-sm text-gray-600 mt-1">
                    Testing: <span className="font-medium">{ruleName}</span>
                  </p>
                )}
              </div>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Input Section */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Capsule URNs (Optional)
              </label>
              <textarea
                value={capsuleUrns}
                onChange={(e) => setCapsuleUrns(e.target.value)}
                placeholder={`Leave empty to test against all capsules, or provide one URN per line:\nurn:dcs:capsule:db:schema:table1\nurn:dcs:capsule:db:schema:table2`}
                rows={5}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="mt-1 text-xs text-gray-500">
                Provide specific capsule URNs to test, or leave empty to test all capsules
              </p>
            </div>

            {/* Test Button */}
            <div className="flex justify-center">
              <button
                onClick={handleTest}
                disabled={isTesting || !ruleId}
                className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isTesting ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Testing Rule...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-5 h-5" />
                    Run Test
                  </>
                )}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-900">Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Results */}
            {testResult && (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Score</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {testResult.score.toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-sm text-green-600 mb-1">Passing</p>
                    <p className="text-2xl font-bold text-green-900">
                      {testResult.summary.passing_rules}
                    </p>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-600 mb-1">Failing</p>
                    <p className="text-2xl font-bold text-red-900">
                      {testResult.summary.failing_rules}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">N/A</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {testResult.summary.not_applicable}
                    </p>
                  </div>
                </div>

                {/* Violations */}
                {testResult.violations.length > 0 ? (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-orange-600" />
                      Violations ({testResult.violation_count})
                    </h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {testResult.violations.map((violation, index) => (
                        <div
                          key={index}
                          className="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={getSeverityVariant(violation.severity)}
                                size="sm"
                              >
                                {violation.severity}
                              </Badge>
                              <Badge variant="default" size="sm">
                                {formatCategory(violation.category)}
                              </Badge>
                            </div>
                            <code className="text-xs font-mono text-gray-600">
                              {violation.subject_type}
                            </code>
                          </div>

                          <h4 className="font-semibold text-gray-900 mb-1">
                            {violation.subject_name}
                          </h4>
                          <p className="text-sm text-gray-700 mb-2">{violation.message}</p>
                          <p className="text-xs font-mono text-gray-500 truncate">
                            {violation.subject_urn}
                          </p>

                          {violation.remediation && (
                            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                              <p className="text-xs font-medium text-blue-900 mb-1">
                                Recommended Action
                              </p>
                              <p className="text-sm text-gray-700">{violation.remediation}</p>
                            </div>
                          )}

                          {Object.keys(violation.details).length > 0 && (
                            <details className="mt-3">
                              <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                                View details
                              </summary>
                              <pre className="mt-2 text-xs bg-gray-50 p-2 rounded border border-gray-200 overflow-x-auto">
                                {JSON.stringify(violation.details, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="p-8 bg-green-50 border border-green-200 rounded-lg text-center">
                    <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-green-900 mb-2">
                      All Tests Passed!
                    </h3>
                    <p className="text-sm text-green-700">
                      No violations found for this rule
                    </p>
                  </div>
                )}

                {/* Metadata */}
                <div className="text-xs text-gray-500 text-center pt-4 border-t border-gray-200">
                  Tested at: {new Date(testResult.computed_at).toLocaleString()}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6 flex items-center justify-end">
            <button
              onClick={handleClose}
              className="px-6 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
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
  switch (severity.toLowerCase()) {
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

function formatCategory(category: string): string {
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
