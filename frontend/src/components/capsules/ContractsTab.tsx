'use client';

/**
 * Contracts Tab Component (Dimension 7: Operational Contract)
 *
 * Displays contract status, SLA tracking, and incident management for a data capsule.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import {
  CapsuleContract,
  SLATarget,
  SLAIncident,
  ContractStatus,
  SchemaPolicy,
  IncidentSeverity,
  IncidentStatus,
} from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Shield,
  Users,
  FileText,
  TrendingUp,
  AlertTriangle,
  XCircle,
} from 'lucide-react';

interface ContractsTabProps {
  capsuleUrn: string;
}

type ContractView = 'contract' | 'sla' | 'incidents';

export default function ContractsTab({ capsuleUrn }: ContractsTabProps) {
  const [view, setView] = useState<ContractView>('contract');

  // Fetch contract data
  const {
    data: contractData,
    isLoading: isLoadingContract,
    error: contractError,
    refetch: refetchContract,
  } = useQuery({
    queryKey: ['capsule-contracts', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: CapsuleContract[] }>(
          `/api/v1/capsule-contracts?capsule_urn=${encodeURIComponent(capsuleUrn)}`
        );
        return response.data;
      } catch (error: any) {
        // Return empty data if endpoint doesn't exist yet
        if (error?.status === 404 || error?.status === 422) {
          return { data: [] };
        }
        throw error;
      }
    },
    retry: false,
    throwOnError: false,
  });

  // Fetch SLA targets
  const {
    data: slaData,
    isLoading: isLoadingSLA,
    error: slaError,
    refetch: refetchSLA,
  } = useQuery({
    queryKey: ['sla-targets', contractData?.data[0]?.id],
    queryFn: async () => {
      if (!contractData?.data[0]?.id) return null;
      try {
        const response = await apiClient.get<{ data: SLATarget[] }>(
          `/api/v1/sla-targets?contract_id=${contractData.data[0].id}`
        );
        return response.data;
      } catch (error: any) {
        // Return empty data if endpoint doesn't exist yet
        if (error?.status === 404 || error?.status === 422) {
          return { data: [] };
        }
        throw error;
      }
    },
    enabled: !!contractData?.data[0]?.id,
    retry: false,
    throwOnError: false,
  });

  // Fetch incidents
  const {
    data: incidentsData,
    isLoading: isLoadingIncidents,
    error: incidentsError,
    refetch: refetchIncidents,
  } = useQuery({
    queryKey: ['sla-incidents', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: SLAIncident[] }>(
          `/api/v1/sla-incidents?capsule_urn=${encodeURIComponent(capsuleUrn)}`
        );
        return response.data;
      } catch (error: any) {
        // Return empty data if endpoint doesn't exist yet
        if (error?.status === 404 || error?.status === 422) {
          return { data: [] };
        }
        throw error;
      }
    },
    retry: false,
    throwOnError: false,
  });

  const contract = contractData?.data[0];
  const slaTargets = slaData?.data || [];
  const incidents = incidentsData?.data || [];

  const isLoading = isLoadingContract || isLoadingSLA || isLoadingIncidents;
  const error = contractError || slaError || incidentsError;

  if (isLoading) {
    return <Loading text="Loading contract data..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load contract data"
        message={error?.message || 'Unknown error'}
        onRetry={() => {
          refetchContract();
          refetchSLA();
          refetchIncidents();
        }}
      />
    );
  }

  if (!contract) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 text-lg mb-2">No Contract Defined</p>
        <p className="text-gray-500 text-sm">
          This capsule does not have an operational contract configured.
        </p>
      </div>
    );
  }

  const openIncidents = incidents.filter((i) => i.status === 'open' || i.status === 'acknowledged');
  const slaCompliance = calculateSLACompliance(slaTargets);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Contract Status */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Contract Status</p>
            {getContractStatusIcon(contract.status)}
          </div>
          <Badge variant={getContractStatusVariant(contract.status)} size="md">
            {contract.status}
          </Badge>
        </div>

        {/* Open Incidents */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Open Incidents</p>
            <AlertCircle className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{openIncidents.length}</p>
        </div>

        {/* SLA Compliance */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">SLA Compliance</p>
            <TrendingUp className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{slaCompliance}%</p>
        </div>

        {/* Consumer Count */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Consumers</p>
            <Users className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{contract.consumer_count}</p>
        </div>
      </div>

      {/* View Selector */}
      <div className="border-b border-gray-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setView('contract')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              view === 'contract'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Contract Details
          </button>
          <button
            onClick={() => setView('sla')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              view === 'sla'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            SLA Tracking
          </button>
          <button
            onClick={() => setView('incidents')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              view === 'incidents'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Incidents ({openIncidents.length})
          </button>
        </div>
      </div>

      {/* Contract Details View */}
      {view === 'contract' && (
        <div className="space-y-6">
          {/* Contract Overview */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Contract Overview</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-gray-600 mb-1">Status</p>
                <Badge variant={getContractStatusVariant(contract.status)} size="md">
                  {contract.status}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Schema Policy</p>
                <Badge variant="default" size="md">
                  {contract.schema_policy || 'Not specified'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Breaking Changes Allowed</p>
                <Badge variant={contract.breaking_change_allowed ? 'warning' : 'success'} size="md">
                  {contract.breaking_change_allowed ? 'Yes' : 'No'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Support Tier</p>
                <p className="text-sm text-gray-900">{contract.support_tier || 'Not specified'}</p>
              </div>
            </div>
          </div>

          {/* Support & Governance */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Shield className="w-5 h-5 mr-2 text-blue-500" />
              Support & Governance
            </h3>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Support Contact</p>
                <p className="text-sm text-gray-900">
                  {contract.support_contact || 'Not specified'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Documentation</p>
                {contract.documentation_url ? (
                  <a
                    href={contract.documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline"
                  >
                    {contract.documentation_url}
                  </a>
                ) : (
                  <p className="text-sm text-gray-400">No documentation URL</p>
                )}
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Consumer Count</p>
                <p className="text-sm text-gray-900">{contract.consumer_count} consumers</p>
              </div>
            </div>
          </div>

          {/* Lifecycle Information */}
          {(contract.deprecation_date || contract.retirement_date) && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-yellow-600" />
                Lifecycle Warnings
              </h3>
              <div className="space-y-2">
                {contract.deprecation_date && (
                  <div className="flex items-start">
                    <Clock className="w-4 h-4 text-yellow-600 mr-2 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">Deprecation Date</p>
                      <p className="text-sm text-gray-600">
                        {new Date(contract.deprecation_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {contract.retirement_date && (
                  <div className="flex items-start">
                    <XCircle className="w-4 h-4 text-red-600 mr-2 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">Retirement Date</p>
                      <p className="text-sm text-gray-600">
                        {new Date(contract.retirement_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SLA Tracking View */}
      {view === 'sla' && (
        <div className="space-y-4">
          {slaTargets.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No SLA targets defined for this contract.</p>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      SLA Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Target
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Current Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Checked
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {slaTargets.map((sla) => (
                    <tr key={sla.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {getSLATypeIcon(sla.sla_type)}
                          <span className="ml-2 text-sm font-medium text-gray-900">
                            {formatSLAType(sla.sla_type)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {sla.target_value} {sla.target_unit}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {sla.current_value !== null
                          ? `${sla.current_value} ${sla.target_unit}`
                          : 'Not measured'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {sla.is_met ? (
                          <Badge variant="success" size="sm">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Met
                          </Badge>
                        ) : (
                          <Badge variant="danger" size="sm">
                            <XCircle className="w-3 h-3 mr-1" />
                            Not Met
                          </Badge>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {sla.last_checked_at
                          ? formatTimestamp(sla.last_checked_at)
                          : 'Never'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Incidents View */}
      {view === 'incidents' && (
        <div className="space-y-4">
          {incidents.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
              <p className="text-gray-600">No incidents recorded for this capsule.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {incidents.map((incident) => (
                <div
                  key={incident.id}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                >
                  {/* Incident Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start space-x-3">
                      {getIncidentSeverityIcon(incident.severity)}
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">{incident.title}</h4>
                        <p className="text-sm text-gray-600">{incident.incident_type}</p>
                      </div>
                    </div>
                    <Badge variant={getIncidentStatusVariant(incident.status)} size="md">
                      {incident.status}
                    </Badge>
                  </div>

                  {/* Incident Details */}
                  <div className="space-y-3">
                    {incident.description && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-1">Description</p>
                        <p className="text-sm text-gray-600">{incident.description}</p>
                      </div>
                    )}

                    {incident.impact && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-1">Impact</p>
                        <p className="text-sm text-gray-600">{incident.impact}</p>
                      </div>
                    )}

                    {incident.root_cause && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-1">Root Cause</p>
                        <p className="text-sm text-gray-600">{incident.root_cause}</p>
                      </div>
                    )}

                    {incident.resolution && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-1">Resolution</p>
                        <p className="text-sm text-gray-600">{incident.resolution}</p>
                      </div>
                    )}

                    {/* Timeline */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Created</p>
                        <p className="text-sm text-gray-900">
                          {formatTimestamp(incident.created_at)}
                        </p>
                      </div>
                      {incident.acknowledged_at && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Acknowledged</p>
                          <p className="text-sm text-gray-900">
                            {formatTimestamp(incident.acknowledged_at)}
                          </p>
                          {incident.acknowledged_by && (
                            <p className="text-xs text-gray-500">{incident.acknowledged_by}</p>
                          )}
                        </div>
                      )}
                      {incident.resolved_at && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Resolved</p>
                          <p className="text-sm text-gray-900">
                            {formatTimestamp(incident.resolved_at)}
                          </p>
                          {incident.resolved_by && (
                            <p className="text-xs text-gray-500">{incident.resolved_by}</p>
                          )}
                        </div>
                      )}
                      {incident.closed_at && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Closed</p>
                          <p className="text-sm text-gray-900">
                            {formatTimestamp(incident.closed_at)}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper Functions

function getContractStatusIcon(status: ContractStatus) {
  switch (status) {
    case 'active':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'draft':
      return <FileText className="w-5 h-5 text-gray-400" />;
    case 'deprecated':
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    case 'retired':
      return <XCircle className="w-5 h-5 text-red-500" />;
  }
}

function getContractStatusVariant(status: ContractStatus): 'success' | 'warning' | 'danger' | 'default' {
  switch (status) {
    case 'active':
      return 'success';
    case 'draft':
      return 'default';
    case 'deprecated':
      return 'warning';
    case 'retired':
      return 'danger';
  }
}

function getIncidentSeverityIcon(severity: IncidentSeverity) {
  switch (severity) {
    case 'critical':
      return <XCircle className="w-6 h-6 text-red-600" />;
    case 'high':
      return <AlertCircle className="w-6 h-6 text-orange-600" />;
    case 'medium':
      return <AlertTriangle className="w-6 h-6 text-yellow-600" />;
    case 'low':
      return <AlertCircle className="w-6 h-6 text-blue-600" />;
  }
}

function getIncidentStatusVariant(status: IncidentStatus): 'danger' | 'warning' | 'info' | 'success' | 'default' {
  switch (status) {
    case 'open':
      return 'danger';
    case 'acknowledged':
      return 'warning';
    case 'investigating':
      return 'info';
    case 'resolved':
      return 'success';
    case 'closed':
      return 'default';
  }
}

function getSLATypeIcon(slaType: string) {
  const iconMap: Record<string, React.JSX.Element> = {
    freshness: <Clock className="w-4 h-4 text-blue-500" />,
    completeness: <CheckCircle className="w-4 h-4 text-green-500" />,
    quality: <Shield className="w-4 h-4 text-purple-500" />,
    availability: <TrendingUp className="w-4 h-4 text-teal-500" />,
    latency: <Clock className="w-4 h-4 text-orange-500" />,
  };
  return iconMap[slaType] || <FileText className="w-4 h-4 text-gray-500" />;
}

function formatSLAType(slaType: string): string {
  return slaType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function calculateSLACompliance(slaTargets: SLATarget[]): number {
  if (slaTargets.length === 0) return 100;
  const metCount = slaTargets.filter((sla) => sla.is_met).length;
  return Math.round((metCount / slaTargets.length) * 100);
}
