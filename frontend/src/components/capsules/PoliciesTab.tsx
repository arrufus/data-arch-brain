'use client';

/**
 * Policies Tab Component (Dimension 5)
 *
 * Displays data policies, masking rules, and compliance information for a capsule.
 * Includes policy governance, data protection, and compliance framework tracking.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import {
  DataPolicy,
  MaskingRule,
  PolicySummary,
  SensitivityLevel,
} from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { Shield, Lock, Globe, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface PoliciesTabProps {
  capsuleUrn: string;
}

type PolicyView = 'policies' | 'masking' | 'compliance';

export default function PoliciesTab({ capsuleUrn }: PoliciesTabProps) {
  const [view, setView] = useState<PolicyView>('policies');

  // Fetch data policies
  const {
    data: policiesData,
    isLoading: policiesLoading,
    error: policiesError,
    refetch: refetchPolicies,
  } = useQuery({
    queryKey: ['data-policies', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: DataPolicy[]; pagination: any }>(
          `/api/v1/data-policies?capsule_urn=${encodeURIComponent(capsuleUrn)}`
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

  // Fetch masking rules
  const {
    data: maskingData,
    isLoading: maskingLoading,
    error: maskingError,
    refetch: refetchMasking,
  } = useQuery({
    queryKey: ['masking-rules', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: MaskingRule[]; pagination: any }>(
          `/api/v1/masking-rules?capsule_urn=${encodeURIComponent(capsuleUrn)}`
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
    enabled: view === 'masking',
    retry: false,
    throwOnError: false,
  });

  const policies = policiesData?.data || [];
  const maskingRules = maskingData?.data || [];

  const isLoading = policiesLoading || (view === 'masking' && maskingLoading);
  const error = policiesError || (view === 'masking' && maskingError);

  if (isLoading) {
    return <Loading text="Loading policy data..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load policy data"
        message={error?.message || 'Unknown error'}
        onRetry={view === 'policies' || view === 'compliance' ? refetchPolicies : refetchMasking}
      />
    );
  }

  // Calculate summary stats
  const policy = policies[0]; // Assuming one policy per capsule
  const allComplianceFrameworks = policies.flatMap((p) => p.compliance_frameworks || []);
  const uniqueFrameworks = Array.from(new Set(allComplianceFrameworks.filter(Boolean)));

  const getSensitivityBadgeVariant = (level: SensitivityLevel | null) => {
    switch (level) {
      case 'restricted':
        return 'danger';
      case 'confidential':
        return 'warning';
      case 'internal':
        return 'info';
      case 'public':
        return 'success';
      default:
        return 'default';
    }
  };

  const getSensitivityIcon = (level: SensitivityLevel | null) => {
    switch (level) {
      case 'restricted':
        return <Lock className="w-4 h-4" />;
      case 'confidential':
        return <Shield className="w-4 h-4" />;
      case 'internal':
        return <AlertTriangle className="w-4 h-4" />;
      case 'public':
        return <Globe className="w-4 h-4" />;
      default:
        return <Shield className="w-4 h-4" />;
    }
  };

  const formatRetentionDays = (days: number | null) => {
    if (!days) return 'Not set';
    if (days < 365) return `${days} days`;
    const years = Math.floor(days / 365);
    const remainingDays = days % 365;
    return remainingDays > 0 ? `${years}y ${remainingDays}d` : `${years} years`;
  };

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Sensitivity Level</p>
              <div className="mt-1">
                {policy?.sensitivity_level ? (
                  <Badge variant={getSensitivityBadgeVariant(policy.sensitivity_level)} size="md">
                    {policy.sensitivity_level.toUpperCase()}
                  </Badge>
                ) : (
                  <span className="text-sm text-gray-400">Not set</span>
                )}
              </div>
            </div>
            {getSensitivityIcon(policy?.sensitivity_level || null)}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Compliance</p>
              <p className="text-2xl font-bold text-gray-900">{uniqueFrameworks.length}</p>
              <p className="text-xs text-gray-500">frameworks</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Masking Rules</p>
              <p className="text-2xl font-bold text-gray-900">{maskingRules.length}</p>
              <p className="text-xs text-gray-500">active rules</p>
            </div>
            <Lock className="w-8 h-8 text-purple-500" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Retention</p>
              <p className="text-sm font-bold text-gray-900">
                {formatRetentionDays(policy?.retention_days || null)}
              </p>
            </div>
            <Clock className="w-8 h-8 text-blue-500" />
          </div>
        </div>
      </div>

      {/* View Selector */}
      <div className="flex items-center gap-2 border-b border-gray-200">
        <button
          onClick={() => setView('policies')}
          className={`px-4 py-2 font-medium transition-colors ${
            view === 'policies'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Policies ({policies.length})
        </button>
        <button
          onClick={() => setView('masking')}
          className={`px-4 py-2 font-medium transition-colors ${
            view === 'masking'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Masking ({maskingRules.length})
        </button>
        <button
          onClick={() => setView('compliance')}
          className={`px-4 py-2 font-medium transition-colors ${
            view === 'compliance'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Compliance ({uniqueFrameworks.length})
        </button>
      </div>

      {/* Policies View */}
      {view === 'policies' && (
        <>
          {policies.length === 0 ? (
            <div className="text-center py-12">
              <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No data policies found.</p>
              <p className="text-sm text-gray-400 mt-2">
                Data policies define how this capsule's data should be protected and governed.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {policies.map((policy) => (
                <div key={policy.id} className="bg-white border border-gray-200 rounded-lg p-6">
                  {/* Policy Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Data Governance Policy</h3>
                      <p className="text-sm text-gray-500 mt-1">Policy ID: {policy.id.substring(0, 8)}...</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {getSensitivityIcon(policy.sensitivity_level)}
                      <Badge variant={getSensitivityBadgeVariant(policy.sensitivity_level)} size="md">
                        {policy.sensitivity_level?.toUpperCase() || 'UNCLASSIFIED'}
                      </Badge>
                    </div>
                  </div>

                  {/* Policy Details Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Left Column */}
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Classification</h4>
                        <div className="flex flex-wrap gap-2">
                          {policy.classification_tags && policy.classification_tags.length > 0 ? (
                            policy.classification_tags.map((tag) => (
                              <Badge key={tag} variant="info" size="sm">
                                {tag}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">No tags</span>
                          )}
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Retention Policy</h4>
                        <div className="space-y-1">
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Duration:</span>{' '}
                            {formatRetentionDays(policy.retention_days)}
                          </p>
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Action:</span>{' '}
                            {policy.deletion_action || 'Not specified'}
                          </p>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Access Control</h4>
                        <div className="space-y-1">
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Min Level:</span>{' '}
                            {policy.min_access_level || 'Not set'}
                          </p>
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Allowed Roles:</span>{' '}
                            {policy.allowed_roles && policy.allowed_roles.length > 0 ? (
                              <span>{policy.allowed_roles.join(', ')}</span>
                            ) : (
                              <span className="text-gray-400">All roles</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Right Column */}
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Data Residency</h4>
                        <div className="space-y-1">
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Location:</span>{' '}
                            {policy.data_residency || 'Not specified'}
                          </p>
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Allowed Regions:</span>{' '}
                            {policy.allowed_regions && policy.allowed_regions.length > 0 ? (
                              <span>{policy.allowed_regions.join(', ')}</span>
                            ) : (
                              <span className="text-gray-400">All regions</span>
                            )}
                          </p>
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">Cross-border Transfer:</span>{' '}
                            {policy.cross_border_transfer ? (
                              <Badge variant="warning" size="sm">
                                Allowed
                              </Badge>
                            ) : (
                              <Badge variant="success" size="sm">
                                Restricted
                              </Badge>
                            )}
                          </p>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Protection Requirements</h4>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            {policy.requires_masking ? (
                              <CheckCircle2 className="w-4 h-4 text-green-600" />
                            ) : (
                              <div className="w-4 h-4 border-2 border-gray-300 rounded" />
                            )}
                            <span className="text-sm text-gray-900">Requires Masking</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {policy.audit_log_required ? (
                              <CheckCircle2 className="w-4 h-4 text-green-600" />
                            ) : (
                              <div className="w-4 h-4 border-2 border-gray-300 rounded" />
                            )}
                            <span className="text-sm text-gray-900">Audit Log Required</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Compliance Frameworks</h4>
                        <div className="flex flex-wrap gap-2">
                          {policy.compliance_frameworks && policy.compliance_frameworks.length > 0 ? (
                            policy.compliance_frameworks.map((framework) => (
                              <Badge key={framework} variant="success" size="sm">
                                {framework}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">None</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Timestamps */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>Created: {new Date(policy.created_at).toLocaleString()}</span>
                      <span>Updated: {new Date(policy.updated_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Masking View */}
      {view === 'masking' && (
        <>
          {maskingRules.length === 0 ? (
            <div className="text-center py-12">
              <Lock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No masking rules found.</p>
              <p className="text-sm text-gray-400 mt-2">
                Masking rules define how sensitive data should be protected when accessed.
              </p>
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
                      Column
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Method
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Applies To Roles
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {maskingRules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{rule.rule_name}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {rule.column_id.substring(0, 8)}...
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge variant="info" size="sm">
                          {rule.masking_method}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {rule.applies_to_roles && rule.applies_to_roles.length > 0 ? (
                            rule.applies_to_roles.map((role) => (
                              <Badge key={role} variant="default" size="sm">
                                {role}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-gray-400">All roles</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                        {new Date(rule.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Compliance View */}
      {view === 'compliance' && (
        <>
          {uniqueFrameworks.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No compliance frameworks configured.</p>
              <p className="text-sm text-gray-400 mt-2">
                Compliance frameworks define regulatory requirements for data handling.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {uniqueFrameworks.map((framework) => (
                <div
                  key={framework}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">{framework}</h3>
                    <Badge variant="success" size="sm">
                      Active
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-gray-600">
                      {framework === 'GDPR' && 'General Data Protection Regulation - EU data protection law'}
                      {framework === 'CCPA' && 'California Consumer Privacy Act - California data privacy law'}
                      {framework === 'HIPAA' && 'Health Insurance Portability and Accountability Act'}
                      {framework === 'SOX' && 'Sarbanes-Oxley Act - Financial data protection'}
                      {framework === 'PCI-DSS' && 'Payment Card Industry Data Security Standard'}
                      {!['GDPR', 'CCPA', 'HIPAA', 'SOX', 'PCI-DSS'].includes(framework) &&
                        'Compliance framework for data governance'}
                    </p>

                    <div className="pt-4 border-t border-gray-200">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                        <span className="text-sm font-medium text-green-600">Compliant</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
