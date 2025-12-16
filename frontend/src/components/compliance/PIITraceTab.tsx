'use client';

/**
 * PII Trace Tab Component
 *
 * Trace PII column lineage to understand data flow and masking status.
 */

import { useState } from 'react';
import { usePIITrace } from '@/lib/api/compliance';
import { Search, ArrowRight, CheckCircle, XCircle, Database } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import Link from 'next/link';

export default function PIITraceTab() {
  const [columnUrn, setColumnUrn] = useState('');
  const [searchUrn, setSearchUrn] = useState<string | null>(null);
  const [maxDepth, setMaxDepth] = useState(10);

  const { data, isLoading, error, refetch } = usePIITrace(searchUrn, maxDepth);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (columnUrn.trim()) {
      setSearchUrn(columnUrn.trim());
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Trace PII Column Lineage</h3>
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label htmlFor="columnUrn" className="block text-sm font-medium text-gray-700 mb-2">
              Column URN
            </label>
            <div className="flex gap-2">
              <input
                id="columnUrn"
                type="text"
                value={columnUrn}
                onChange={(e) => setColumnUrn(e.target.value)}
                placeholder="urn:dab:dbt:model:schema.table:column_name"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                type="submit"
                disabled={!columnUrn.trim()}
                className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Search className="w-4 h-4" />
                Trace
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label htmlFor="maxDepth" className="text-sm font-medium text-gray-700">
              Max Depth:
            </label>
            <select
              id="maxDepth"
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="5">5 levels</option>
              <option value="10">10 levels</option>
              <option value="15">15 levels</option>
              <option value="20">20 levels</option>
            </select>
          </div>
        </form>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong>Tip:</strong> Enter a column URN to trace its lineage and see where PII data flows and
            whether it's masked at terminal nodes.
          </p>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && <Loading text="Tracing PII lineage..." />}

      {/* Error State */}
      {error && (
        <ErrorMessage
          title="Failed to trace PII"
          message={error?.message || 'Unknown error'}
          onRetry={refetch}
        />
      )}

      {/* Results */}
      {data && (
        <div className="space-y-6">
          {/* Column Info */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Column Details</h3>
            <div className="space-y-2">
              <div>
                <span className="text-sm text-gray-600">Column:</span>{' '}
                <span className="font-medium text-gray-900">{data.column.column_name}</span>
              </div>
              <div>
                <span className="text-sm text-gray-600">Capsule:</span>{' '}
                <Link
                  href={`/capsules/${encodeURIComponent(data.column.capsule_urn)}`}
                  className="font-medium text-blue-600 hover:underline"
                >
                  {data.column.capsule_name}
                </Link>
              </div>
              <div>
                <span className="text-sm text-gray-600">PII Type:</span>{' '}
                {data.column.pii_type ? (
                  <Badge variant="pii" size="sm">
                    {data.column.pii_type}
                  </Badge>
                ) : (
                  <span className="text-gray-500">None</span>
                )}
              </div>
              <div>
                <span className="text-sm text-gray-600">Layer:</span>{' '}
                {data.column.capsule_layer ? (
                  <Badge variant={data.column.capsule_layer as any} size="sm">
                    {data.column.capsule_layer}
                  </Badge>
                ) : (
                  <span className="text-gray-500">Unknown</span>
                )}
              </div>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Database className="w-4 h-4 text-gray-600" />
                <span className="text-sm text-gray-600">Total Nodes</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {(data.origin ? 1 : 0) + data.propagation_path.length + data.terminals.length}
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm text-gray-600">Masked at Terminals</span>
              </div>
              <p className="text-2xl font-bold text-green-900">
                {data.terminals.filter((n) => n.is_masked).length}
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <XCircle className="w-4 h-4 text-red-600" />
                <span className="text-sm text-gray-600">Unmasked at Terminals</span>
              </div>
              <p className="text-2xl font-bold text-red-900">
                {data.terminals.filter((n) => !n.is_masked).length}
              </p>
            </div>
          </div>

          {/* Origin */}
          {data.origin && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-600" />
                Origin
              </h3>
              <TraceNodeCard node={data.origin} />
            </div>
          )}

          {/* Propagation Path */}
          {data.propagation_path.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <ArrowRight className="w-5 h-5 text-gray-600" />
                Propagation Path ({data.propagation_path.length} intermediate nodes)
              </h3>
              <div className="space-y-2">
                {data.propagation_path.map((node, index) => (
                  <div key={`${node.urn}-${index}`} className="flex items-center gap-2">
                    <div className="flex-shrink-0 text-gray-400">
                      <ArrowRight className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <TraceNodeCard node={node} compact />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Terminals */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              Terminal Nodes ({data.terminals.length})
            </h3>
            {data.terminals.length > 0 ? (
              <div className="space-y-2">
                {data.terminals.map((node, index) => (
                  <TraceNodeCard key={`${node.urn}-${index}`} node={node} />
                ))}
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                <p className="text-gray-600">No downstream consumers found for this PII column.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!searchUrn && !isLoading && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Trace Results</h3>
          <p className="text-gray-600">Enter a column URN above to trace its PII lineage</p>
        </div>
      )}
    </div>
  );
}

// Trace Node Card Component
function TraceNodeCard({ node, compact = false }: { node: any; compact?: boolean }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg flex-shrink-0">
          <Database className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Link
              href={`/capsules/${encodeURIComponent(node.urn.split(':').slice(0, -1).join(':'))}`}
              className="font-medium text-gray-900 hover:underline truncate"
            >
              {node.capsule_name}
            </Link>
            {node.layer && (
              <Badge variant={node.layer as any} size="sm">
                {node.layer}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <p className="text-sm text-gray-900">{node.name}</p>
            {node.pii_type && (
              <Badge variant="pii" size="sm">
                {node.pii_type}
              </Badge>
            )}
            {node.is_masked ? (
              <div className="flex items-center gap-1 text-green-600">
                <CheckCircle className="w-3 h-3" />
                <span className="text-xs font-medium">Masked</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-red-600">
                <XCircle className="w-3 h-3" />
                <span className="text-xs font-medium">Unmasked</span>
              </div>
            )}
          </div>
          {!compact && (
            <p className="text-xs text-gray-500 font-mono mt-1 truncate">{node.urn}</p>
          )}
        </div>
        <div className="text-xs text-gray-500">Depth: {node.depth}</div>
      </div>
    </div>
  );
}
