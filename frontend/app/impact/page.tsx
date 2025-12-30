'use client';

/**
 * Impact Analysis Page
 *
 * Analyze downstream impact of changes to data capsules.
 * Shows "what-if" analysis and affected capsule highlighting.
 * Now includes task-level impact analysis for Airflow pipelines.
 */

import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { AlertCircle, Search, ChevronDown, X, Target, TrendingDown, Layers, GitBranch, Workflow } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import Link from 'next/link';
import TaskImpactAnalysis from '@/components/impact/TaskImpactAnalysis';

type ViewMode = 'capsule' | 'task';
type ChangeType = 'delete' | 'rename' | 'type_change' | 'nullability' | 'default';

export default function ImpactAnalysisPage() {
  // View mode toggle
  const [viewMode, setViewMode] = useState<ViewMode>('capsule');

  // Capsule impact state
  const [selectedCapsuleUrn, setSelectedCapsuleUrn] = useState<string | null>(null);
  const [capsuleSearch, setCapsuleSearch] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [maxDepth, setMaxDepth] = useState(5);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Task impact state
  const [selectedColumnUrn, setSelectedColumnUrn] = useState<string | null>(null);
  const [columnSearch, setColumnSearch] = useState('');
  const [isColumnDropdownOpen, setIsColumnDropdownOpen] = useState(false);
  const [changeType, setChangeType] = useState<ChangeType>('rename');
  const columnDropdownRef = useRef<HTMLDivElement>(null);

  // Handle click outside to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
      if (columnDropdownRef.current && !columnDropdownRef.current.contains(event.target as Node)) {
        setIsColumnDropdownOpen(false);
      }
    };

    if (isDropdownOpen || isColumnDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen, isColumnDropdownOpen]);

  // Fetch capsules for type-ahead dropdown
  const { data: capsulesData, isLoading: isLoadingCapsules } = useQuery({
    queryKey: ['capsules-search', capsuleSearch],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/capsules', {
        params: {
          search: capsuleSearch || undefined,
          limit: capsuleSearch ? 10 : 20,
        },
      });
      return response.data;
    },
    enabled: isDropdownOpen,
  });

  // Fetch columns for task impact column selection
  const { data: columnsData, isLoading: isLoadingColumns } = useQuery({
    queryKey: ['columns-search', columnSearch],
    queryFn: async () => {
      // Get all capsules first, then fetch columns for each
      const capsulesResponse = await apiClient.get('/api/v1/capsules', {
        params: {
          search: columnSearch || undefined,
          limit: 20,
        },
      });

      // Flatten columns from all capsules
      const allColumns: any[] = [];
      for (const capsule of capsulesResponse.data.data || []) {
        if (capsule.urn) {
          try {
            const columnsResponse = await apiClient.get(
              `/api/v1/capsules/${encodeURIComponent(capsule.urn)}/columns`
            );
            // Fix: Access nested data property - API returns { data: [...], pagination: {...} }
            const columns = columnsResponse.data.data || [];
            allColumns.push(...columns.map((col: any) => ({
              ...col,
              capsule_name: capsule.name,
              capsule_urn: capsule.urn,
            })));
          } catch (err) {
            // Skip capsules without columns
            console.warn(`Failed to fetch columns for ${capsule.name}:`, err);
          }
        }
      }

      // Filter columns based on search
      const filteredColumns = allColumns.filter((col: any) =>
        !columnSearch ||
        col.name?.toLowerCase().includes(columnSearch.toLowerCase()) ||
        col.capsule_name?.toLowerCase().includes(columnSearch.toLowerCase())
      );

      console.log(`Found ${allColumns.length} total columns, ${filteredColumns.length} after filtering`);
      return filteredColumns;
    },
    enabled: isColumnDropdownOpen,
  });

  // Fetch lineage (downstream only) for impact analysis
  const { data: impactData, isLoading: isLoadingImpact, error: impactError, refetch } = useQuery({
    queryKey: ['impact-analysis', selectedCapsuleUrn, maxDepth],
    queryFn: async () => {
      if (!selectedCapsuleUrn) return null;

      const response = await apiClient.get(
        `/api/v1/capsules/${encodeURIComponent(selectedCapsuleUrn)}/lineage`,
        {
          params: {
            direction: 'downstream',
            depth: maxDepth,
          },
        }
      );
      return response.data;
    },
    enabled: !!selectedCapsuleUrn,
  });

  // Get selected capsule details
  const { data: capsuleData } = useQuery({
    queryKey: ['capsule-detail', selectedCapsuleUrn],
    queryFn: async () => {
      if (!selectedCapsuleUrn) return null;

      const response = await apiClient.get(
        `/api/v1/capsules/${encodeURIComponent(selectedCapsuleUrn)}/detail`
      );
      return response.data;
    },
    enabled: !!selectedCapsuleUrn,
  });

  const downstreamNodes = impactData?.nodes?.filter((n: any) => n.direction === 'downstream') || [];
  const edges = impactData?.edges || [];

  // Group nodes by depth
  const nodesByDepth: Record<number, any[]> = {};
  downstreamNodes.forEach((node: any) => {
    if (!nodesByDepth[node.depth]) {
      nodesByDepth[node.depth] = [];
    }
    nodesByDepth[node.depth].push(node);
  });

  // Calculate impact statistics
  const impactStats = {
    totalAffected: downstreamNodes.length,
    maxDepth: Math.max(0, ...downstreamNodes.map((n: any) => n.depth)),
    byLayer: downstreamNodes.reduce((acc: any, node: any) => {
      const layer = node.layer || 'unknown';
      acc[layer] = (acc[layer] || 0) + 1;
      return acc;
    }, {}),
    byType: downstreamNodes.reduce((acc: any, node: any) => {
      acc[node.type] = (acc[node.type] || 0) + 1;
      return acc;
    }, {}),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Target className="w-8 h-8 text-purple-600" />
          Impact Analysis
        </h1>
        <p className="mt-2 text-gray-600">
          Analyze downstream impact of changes to data capsules and Airflow tasks
        </p>
      </div>

      {/* View Mode Toggle */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('capsule')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'capsule'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <GitBranch className="w-4 h-4" />
            Capsule Impact
          </button>
          <button
            onClick={() => setViewMode('task')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'task'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Workflow className="w-4 h-4" />
            Task Impact (Airflow)
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          {viewMode === 'capsule'
            ? 'Analyze which capsules are affected by changes to other capsules'
            : 'Analyze which Airflow tasks are affected by schema changes to columns'}
        </p>
      </div>

      {/* Capsule Impact View */}
      {viewMode === 'capsule' && (
        <>
          {/* Capsule Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Select Source Capsule
            </h2>

        {selectedCapsuleUrn ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex-1">
                <p className="font-medium text-purple-900">
                  {capsuleData?.name || selectedCapsuleUrn.split(':').pop()}
                </p>
                <p className="text-sm text-purple-700 font-mono">{selectedCapsuleUrn}</p>
                {capsuleData && (
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant={capsuleData.capsule_type} size="sm">
                      {capsuleData.capsule_type}
                    </Badge>
                    {capsuleData.layer && (
                      <Badge variant={capsuleData.layer} size="sm">
                        {capsuleData.layer}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={() => {
                  setSelectedCapsuleUrn(null);
                  setCapsuleSearch('');
                }}
                className="text-purple-600 hover:text-purple-800"
                title="Clear selection"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Analysis Depth
              </label>
              <select
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="1">1 level (immediate dependents)</option>
                <option value="2">2 levels</option>
                <option value="3">3 levels</option>
                <option value="5">5 levels</option>
                <option value="10">10 levels (full impact)</option>
              </select>
            </div>
          </div>
        ) : (
          <div ref={dropdownRef} className="relative">
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <span className="text-gray-500">
                {capsuleSearch || 'Select a capsule...'}
              </span>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                <div className="p-2 border-b border-gray-200">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Type to search..."
                      value={capsuleSearch}
                      onChange={(e) => setCapsuleSearch(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      autoFocus
                    />
                  </div>
                </div>

                <div className="max-h-60 overflow-y-auto">
                  {isLoadingCapsules ? (
                    <div className="px-4 py-8 text-center text-gray-500">
                      Loading capsules...
                    </div>
                  ) : capsulesData?.data && capsulesData.data.length > 0 ? (
                    capsulesData.data.map((capsule: any) => (
                      <button
                        key={capsule.urn}
                        onClick={() => {
                          setSelectedCapsuleUrn(capsule.urn);
                          setCapsuleSearch('');
                          setIsDropdownOpen(false);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                      >
                        <div className="font-medium text-gray-900">{capsule.name}</div>
                        <div className="text-xs text-gray-500 truncate">{capsule.urn}</div>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-8 text-center text-gray-500">
                      {capsuleSearch ? 'No capsules found' : 'No capsules available'}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Impact Analysis Results */}
      {selectedCapsuleUrn && (
        <>
          {isLoadingImpact ? (
            <div className="flex items-center justify-center py-12">
              <Loading text="Analyzing impact..." />
            </div>
          ) : impactError ? (
            <ErrorMessage
              title="Failed to analyze impact"
              message={impactError?.message || 'Unknown error'}
              onRetry={refetch}
            />
          ) : downstreamNodes.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No Downstream Impact
              </h3>
              <p className="text-gray-600">
                This capsule has no downstream dependents. Changes will not affect other capsules.
              </p>
            </div>
          ) : (
            <>
              {/* Impact Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">Affected Capsules</span>
                    <TrendingDown className="w-4 h-4 text-purple-600" />
                  </div>
                  <p className="text-3xl font-bold text-purple-600">
                    {impactStats.totalAffected}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Downstream dependents
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">Impact Depth</span>
                    <Layers className="w-4 h-4 text-blue-600" />
                  </div>
                  <p className="text-3xl font-bold text-blue-600">
                    {impactStats.maxDepth}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Levels deep
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">Gold Layer Impact</span>
                    <AlertCircle className="w-4 h-4 text-yellow-600" />
                  </div>
                  <p className="text-3xl font-bold text-yellow-600">
                    {impactStats.byLayer.gold || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Production capsules
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600">Critical Path</span>
                    <Target className="w-4 h-4 text-red-600" />
                  </div>
                  <p className="text-3xl font-bold text-red-600">
                    {Object.keys(nodesByDepth).length}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Propagation stages
                  </p>
                </div>
              </div>

              {/* Impact Breakdown by Type */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Impact Breakdown by Type
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(impactStats.byType).map(([type, count]) => (
                    <div key={type} className="border border-gray-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-600 capitalize">{type}</p>
                      <p className="text-2xl font-bold text-gray-900">{count as number}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Affected Capsules by Depth */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Affected Capsules (Propagation Order)
                  </h3>
                  <Link
                    href={`/lineage?capsule=${encodeURIComponent(selectedCapsuleUrn)}`}
                    className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                  >
                    View in Lineage Graph →
                  </Link>
                </div>

                <div className="space-y-6">
                  {Object.entries(nodesByDepth)
                    .sort(([a], [b]) => Number(a) - Number(b))
                    .map(([depth, nodes]: [string, any]) => (
                      <div key={depth}>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-700 font-bold text-sm">
                            {depth}
                          </div>
                          <h4 className="font-medium text-gray-900">
                            Level {depth} ({nodes.length} capsule{nodes.length !== 1 ? 's' : ''})
                          </h4>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 ml-11">
                          {nodes.map((node: any) => (
                            <Link
                              key={node.urn}
                              href={`/capsules/${encodeURIComponent(node.urn)}`}
                              className="border border-gray-200 rounded-lg p-3 hover:border-purple-300 hover:shadow-md transition-all"
                            >
                              <div className="flex items-start justify-between gap-2 mb-2">
                                <p className="font-medium text-gray-900 text-sm truncate">
                                  {node.name}
                                </p>
                                <div className="flex gap-1">
                                  <Badge variant={node.type as any} size="sm">
                                    {node.type}
                                  </Badge>
                                </div>
                              </div>
                              {node.layer && (
                                <Badge variant={node.layer as any} size="sm">
                                  {node.layer}
                                </Badge>
                              )}
                              <p className="text-xs text-gray-500 font-mono truncate mt-1">
                                {node.urn}
                              </p>
                            </Link>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Impact Warnings */}
              {(impactStats.byLayer.gold > 0 || impactStats.totalAffected > 10) && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-yellow-900 mb-1">
                        High Impact Change Detected
                      </h4>
                      <ul className="text-sm text-yellow-800 space-y-1">
                        {impactStats.byLayer.gold > 0 && (
                          <li>
                            • This change affects <strong>{impactStats.byLayer.gold}</strong> production (gold layer) capsule
                            {impactStats.byLayer.gold !== 1 ? 's' : ''}
                          </li>
                        )}
                        {impactStats.totalAffected > 10 && (
                          <li>
                            • This change has a wide impact radius (<strong>{impactStats.totalAffected}</strong> affected capsules)
                          </li>
                        )}
                        {impactStats.maxDepth > 3 && (
                          <li>
                            • Changes propagate through <strong>{impactStats.maxDepth}</strong> levels of transformation
                          </li>
                        )}
                      </ul>
                      <p className="text-sm text-yellow-800 mt-2">
                        <strong>Recommendation:</strong> Coordinate with downstream consumers and consider implementing
                        breaking change strategies (versioning, deprecation periods, migration guides).
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

          {/* Help Section */}
          {!selectedCapsuleUrn && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="font-semibold text-blue-900 mb-2">How to Use Capsule Impact Analysis</h3>
              <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
                <li>Select a source capsule using the search dropdown above</li>
                <li>Choose the analysis depth (how many levels downstream to analyze)</li>
                <li>Review the impact statistics and affected capsules</li>
                <li>Click on any affected capsule to view its details</li>
                <li>Use the "View in Lineage Graph" link to see the visual representation</li>
              </ol>
              <p className="text-sm text-blue-800 mt-3">
                <strong>Use Case:</strong> Before making breaking changes to a capsule, use this tool to understand
                the blast radius and coordinate with affected downstream teams.
              </p>
            </div>
          )}
        </>
      )}

      {/* Task Impact View */}
      {viewMode === 'task' && (
        <>
          {/* Column Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Select Column and Change Type
            </h2>

            {selectedColumnUrn ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium text-blue-900">
                      {selectedColumnUrn.split(':').pop()}
                    </p>
                    <p className="text-sm text-blue-700 font-mono">{selectedColumnUrn}</p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedColumnUrn(null);
                      setColumnSearch('');
                    }}
                    className="text-blue-600 hover:text-blue-800"
                    title="Clear selection"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Change Type
                  </label>
                  <select
                    value={changeType}
                    onChange={(e) => setChangeType(e.target.value as ChangeType)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="delete">Delete Column (Highest Risk)</option>
                    <option value="rename">Rename Column</option>
                    <option value="type_change">Change Data Type</option>
                    <option value="nullability">Change Nullability</option>
                    <option value="default">Change Default Value (Lowest Risk)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Select the type of schema change you plan to make
                  </p>
                </div>
              </div>
            ) : (
              <div ref={columnDropdownRef} className="relative">
                <button
                  type="button"
                  onClick={() => setIsColumnDropdownOpen(!isColumnDropdownOpen)}
                  className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <span className="text-gray-500">
                    {columnSearch || 'Select a column...'}
                  </span>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isColumnDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {isColumnDropdownOpen && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                    <div className="p-2 border-b border-gray-200">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Type to search columns..."
                          value={columnSearch}
                          onChange={(e) => setColumnSearch(e.target.value)}
                          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                          autoFocus
                        />
                      </div>
                    </div>

                    <div className="max-h-60 overflow-y-auto">
                      {isLoadingColumns ? (
                        <div className="px-4 py-8 text-center text-gray-500">
                          Loading columns...
                        </div>
                      ) : columnsData && columnsData.length > 0 ? (
                        columnsData.map((column: any) => (
                          <button
                            key={column.urn}
                            onClick={() => {
                              setSelectedColumnUrn(column.urn);
                              setColumnSearch('');
                              setIsColumnDropdownOpen(false);
                            }}
                            className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                          >
                            <div className="font-medium text-gray-900">
                              {column.capsule_name || 'Unknown'} → {column.name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {column.data_type}
                              {column.description && ` • ${column.description}`}
                            </div>
                            <div className="text-xs text-gray-400 truncate font-mono">{column.urn}</div>
                          </button>
                        ))
                      ) : (
                        <div className="px-4 py-8 text-center text-gray-500">
                          {columnSearch ? 'No columns found' : 'No columns available'}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Task Impact Analysis Component */}
          {selectedColumnUrn && (
            <TaskImpactAnalysis
              columnUrn={selectedColumnUrn}
              changeType={changeType}
              depth={5}
            />
          )}

          {/* Help Section */}
          {!selectedColumnUrn && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="font-semibold text-blue-900 mb-2">How to Use Task Impact Analysis</h3>
              <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
                <li>Select a column using the search dropdown above</li>
                <li>Choose the type of schema change you plan to make</li>
                <li>Click "Analyze Impact" to see which Airflow tasks will be affected</li>
                <li>Review risk scores, execution schedules, and temporal impact</li>
                <li>Use the recommended maintenance windows to minimize disruption</li>
              </ol>
              <p className="text-sm text-blue-800 mt-3">
                <strong>Use Case:</strong> Before making schema changes to a column, use this tool to understand
                which Airflow tasks will break and when is the best time to deploy the change.
              </p>
              <p className="text-sm text-blue-800 mt-2">
                <strong>Example:</strong> Renaming the <code className="bg-blue-100 px-1 rounded">account_code</code> column
                in <code className="bg-blue-100 px-1 rounded">chart_of_accounts</code> will show you all the tasks
                that read from this column and calculate the risk of breaking them.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
