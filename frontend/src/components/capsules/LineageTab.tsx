'use client';

/**
 * Lineage Tab Component (Dimension 6: Provenance & Lineage)
 *
 * Displays upstream/downstream lineage, version history, and transformation code.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { LineageGraph, CapsuleVersion, TransformationCode } from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { ArrowRight, ArrowLeft, Database, GitBranch, History, Code2, FileCode } from 'lucide-react';
import Link from 'next/link';

interface LineageTabProps {
  capsuleUrn: string;
}

type LineageView = 'lineage' | 'versions' | 'code';

export default function LineageTab({ capsuleUrn }: LineageTabProps) {
  const [view, setView] = useState<LineageView>('lineage');
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both');
  const [depth, setDepth] = useState(3);

  // Fetch lineage
  const { data: lineage, isLoading: isLoadingLineage, error: lineageError, refetch: refetchLineage } = useQuery({
    queryKey: ['capsule-lineage', capsuleUrn, direction, depth],
    queryFn: async () => {
      const response = await apiClient.get<LineageGraph>(
        `/api/v1/capsules/${encodeURIComponent(capsuleUrn)}/lineage`,
        {
          params: { direction, depth },
        }
      );
      return response.data;
    },
    enabled: view === 'lineage',
  });

  // Fetch capsule versions
  const { data: versionsData, isLoading: isLoadingVersions, error: versionsError, refetch: refetchVersions } = useQuery({
    queryKey: ['capsule-versions', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: CapsuleVersion[] }>(
          `/api/v1/capsule-versions?capsule_urn=${encodeURIComponent(capsuleUrn)}`
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
    enabled: view === 'versions',
    retry: false,
    throwOnError: false,
  });

  // Fetch transformation code
  const { data: codeData, isLoading: isLoadingCode, error: codeError, refetch: refetchCode } = useQuery({
    queryKey: ['transformation-code', capsuleUrn],
    queryFn: async () => {
      try {
        const response = await apiClient.get<{ data: TransformationCode[] }>(
          `/api/v1/transformation-code?capsule_urn=${encodeURIComponent(capsuleUrn)}`
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
    enabled: view === 'code',
    retry: false,
    throwOnError: false,
  });

  const versions = versionsData?.data || [];
  const codeFiles = codeData?.data || [];

  const isLoading = isLoadingLineage || isLoadingVersions || isLoadingCode;
  const error = lineageError || versionsError || codeError;

  if (isLoading) {
    return <Loading text={`Loading ${view}...`} />;
  }

  if (error) {
    return (
      <ErrorMessage
        title={`Failed to load ${view}`}
        message={error?.message || 'Unknown error'}
        onRetry={() => {
          refetchLineage();
          refetchVersions();
          refetchCode();
        }}
      />
    );
  }

  // Separate nodes by direction using the node's direction property
  const upstream = lineage?.nodes.filter(
    (node) => node.direction === 'upstream'
  ) || [];
  const downstream = lineage?.nodes.filter(
    (node) => node.direction === 'downstream'
  ) || [];

  return (
    <div className="space-y-6">
      {/* View Selector */}
      <div className="border-b border-gray-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setView('lineage')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
              view === 'lineage'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <GitBranch className="w-4 h-4" />
            Lineage
          </button>
          <button
            onClick={() => setView('versions')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
              view === 'versions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <History className="w-4 h-4" />
            Versions ({versions.length})
          </button>
          <button
            onClick={() => setView('code')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
              view === 'code'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Code2 className="w-4 h-4" />
            Code ({codeFiles.length})
          </button>
        </div>
      </div>

      {/* Lineage View */}
      {view === 'lineage' && (
        <div className="space-y-6">
          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Direction
            </label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="both">Both</option>
              <option value="upstream">Upstream Only</option>
              <option value="downstream">Downstream Only</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Depth
            </label>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="1">1 level</option>
              <option value="2">2 levels</option>
              <option value="3">3 levels</option>
              <option value="5">5 levels</option>
            </select>
          </div>
        </div>

        <Link
          href={`/lineage?capsule=${encodeURIComponent(capsuleUrn)}`}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <GitBranch className="w-4 h-4" />
          View in Interactive Graph
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <ArrowLeft className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-600">Upstream Sources</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{upstream.length}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <ArrowRight className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-600">Downstream Dependents</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{downstream.length}</p>
        </div>
      </div>

      {/* Upstream List */}
      {(direction === 'upstream' || direction === 'both') && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <ArrowLeft className="w-5 h-5 text-gray-600" />
            Upstream Sources ({upstream.length})
          </h3>
          {upstream.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">No upstream sources found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {upstream.map((node) => (
                <LineageNodeCard key={node.urn} node={node} />
              ))}
            </div>
          )}
        </div>
      )}

          {/* Downstream List */}
          {(direction === 'downstream' || direction === 'both') && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <ArrowRight className="w-5 h-5 text-gray-600" />
                Downstream Dependents ({downstream.length})
              </h3>
              {downstream.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <p className="text-gray-500">No downstream dependents found</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {downstream.map((node) => (
                    <LineageNodeCard key={node.urn} node={node} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Versions View */}
      {view === 'versions' && (
        <div className="space-y-4">
          {versions.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 text-lg mb-2">No Version History</p>
              <p className="text-gray-500 text-sm">
                This capsule does not have version tracking enabled.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {versions.map((version, index) => (
                <div
                  key={version.id}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                >
                  {/* Version Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                        <History className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">
                          Version {version.version_number}
                          {version.version_name && (
                            <span className="text-gray-600 font-normal ml-2">
                              ({version.version_name})
                            </span>
                          )}
                        </h4>
                        <p className="text-sm text-gray-600">{version.change_summary}</p>
                      </div>
                    </div>
                    {index === 0 && (
                      <Badge variant="success" size="md">
                        Latest
                      </Badge>
                    )}
                  </div>

                  {/* Version Details */}
                  <div className="space-y-3">
                    {version.change_type && (
                      <div className="flex items-center gap-2">
                        <Badge variant={getChangeTypeVariant(version.change_type)} size="sm">
                          {formatChangeType(version.change_type)}
                        </Badge>
                      </div>
                    )}

                    {version.change_details && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-600 mb-2">Change Details</p>
                        <pre className="text-xs text-gray-900 font-mono overflow-x-auto">
                          {JSON.stringify(version.change_details, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Git Information */}
                    {(version.git_commit_sha || version.git_branch || version.git_author) && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-3 border-t border-gray-200">
                        {version.git_commit_sha && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Commit SHA</p>
                            <p className="text-sm font-mono text-gray-900 truncate">
                              {version.git_commit_sha.substring(0, 8)}
                            </p>
                          </div>
                        )}
                        {version.git_branch && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Branch</p>
                            <p className="text-sm text-gray-900">{version.git_branch}</p>
                          </div>
                        )}
                        {version.git_author && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Author</p>
                            <p className="text-sm text-gray-900">{version.git_author}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Timestamp */}
                    <div className="text-xs text-gray-500 pt-2 border-t border-gray-200">
                      Created: {new Date(version.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Code View */}
      {view === 'code' && (
        <div className="space-y-4">
          {codeFiles.length === 0 ? (
            <div className="text-center py-12">
              <Code2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 text-lg mb-2">No Transformation Code</p>
              <p className="text-gray-500 text-sm">
                This capsule does not have transformation code registered.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {codeFiles.map((code) => (
                <div
                  key={code.id}
                  className="bg-white border border-gray-200 rounded-lg overflow-hidden"
                >
                  {/* Code Header */}
                  <div className="bg-gray-50 border-b border-gray-200 px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileCode className="w-5 h-5 text-gray-600" />
                        <div>
                          <h4 className="font-semibold text-gray-900">
                            {code.file_path || 'Inline Code'}
                          </h4>
                          <p className="text-sm text-gray-600">Type: {code.code_type}</p>
                        </div>
                      </div>
                      <Badge variant={getCodeTypeVariant(code.code_type)} size="md">
                        {code.code_type?.toUpperCase() || 'UNKNOWN'}
                      </Badge>
                    </div>

                    {/* Git Information */}
                    {(code.git_url || code.git_ref) && (
                      <div className="mt-3 flex items-center gap-4 text-sm">
                        {code.git_url && (
                          <a
                            href={code.git_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            View on Git
                          </a>
                        )}
                        {code.git_ref && (
                          <span className="text-gray-600">
                            Ref: <span className="font-mono">{code.git_ref}</span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Code Content */}
                  <div className="p-6 bg-gray-900 overflow-x-auto">
                    <pre className="text-sm text-gray-100 font-mono">
                      <code>{code.code_content}</code>
                    </pre>
                  </div>

                  {/* Footer */}
                  <div className="bg-gray-50 border-t border-gray-200 px-6 py-3">
                    <p className="text-xs text-gray-500">
                      Last updated: {new Date(code.updated_at).toLocaleString()}
                    </p>
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

function getChangeTypeVariant(changeType: string): 'danger' | 'warning' | 'info' | 'default' {
  switch (changeType) {
    case 'schema_change':
      return 'danger';
    case 'code_change':
      return 'warning';
    case 'data_change':
      return 'info';
    case 'config_change':
      return 'default';
    default:
      return 'default';
  }
}

function formatChangeType(changeType: string): string {
  return changeType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getCodeTypeVariant(codeType: string): 'info' | 'warning' | 'success' | 'default' {
  switch (codeType) {
    case 'sql':
      return 'info';
    case 'python':
      return 'warning';
    case 'dbt':
      return 'success';
    case 'spark':
      return 'warning';
    default:
      return 'default';
  }
}

// Lineage Node Card Component
function LineageNodeCard({ node }: { node: { urn: string; name: string; type: string; layer: string | null; depth: number } }) {
  return (
    <Link
      href={`/capsules/${encodeURIComponent(node.urn)}`}
      className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg flex-shrink-0">
          <Database className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="font-medium text-gray-900 truncate">{node.name}</p>
            <Badge variant={node.type as any} size="sm">
              {node.type}
            </Badge>
            {node.layer && (
              <Badge variant={node.layer as any} size="sm">
                {node.layer}
              </Badge>
            )}
          </div>
          <p className="text-xs text-gray-500 font-mono truncate">{node.urn}</p>
        </div>
        <div className="text-xs text-gray-500">
          Depth: {node.depth}
        </div>
      </div>
    </Link>
  );
}
