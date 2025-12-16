'use client';

/**
 * Lineage Tab Component
 *
 * Displays upstream and downstream lineage for a capsule (simple list view for MVP).
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { LineageGraph } from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import { ArrowRight, ArrowLeft, Database, GitBranch } from 'lucide-react';
import Link from 'next/link';

interface LineageTabProps {
  capsuleUrn: string;
}

export default function LineageTab({ capsuleUrn }: LineageTabProps) {
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both');
  const [depth, setDepth] = useState(3);

  // Fetch lineage
  const { data: lineage, isLoading, error, refetch } = useQuery({
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
  });

  if (isLoading) {
    return <Loading text="Loading lineage..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load lineage"
        message={error?.message || 'Unknown error'}
        onRetry={refetch}
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
  );
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
