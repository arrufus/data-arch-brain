'use client';

/**
 * Redundancy Detection Page
 *
 * Find duplicate and similar capsules to reduce data redundancy.
 */

import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Copy, Search, ChevronDown, X, AlertCircle, TrendingDown, Layers, CheckCircle2 } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import Link from 'next/link';

type TabType = 'report' | 'finder' | 'compare';

export default function RedundancyPage() {
  const [activeTab, setActiveTab] = useState<TabType>('report');
  const [selectedCapsuleUrn, setSelectedCapsuleUrn] = useState<string | null>(null);
  const [capsuleSearch, setCapsuleSearch] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [threshold, setThreshold] = useState(0.75);
  const [sameTypeOnly, setSameTypeOnly] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  // Fetch redundancy report
  const { data: reportData, isLoading: isLoadingReport, error: reportError, refetch: refetchReport } = useQuery({
    queryKey: ['redundancy-report'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/redundancy/report');
      return response.data;
    },
    enabled: activeTab === 'report',
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch capsules for dropdown
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
    enabled: isDropdownOpen && activeTab === 'finder',
  });

  // Find similar capsules
  const { data: similarData, isLoading: isLoadingSimilar, refetch: refetchSimilar } = useQuery({
    queryKey: ['similar-capsules', selectedCapsuleUrn, threshold, sameTypeOnly],
    queryFn: async () => {
      if (!selectedCapsuleUrn) return null;

      const response = await apiClient.get(
        `/api/v1/redundancy/capsules/${encodeURIComponent(selectedCapsuleUrn)}/similar`,
        {
          params: {
            threshold,
            limit: 20,
            same_type_only: sameTypeOnly,
          },
        }
      );
      return response.data;
    },
    enabled: !!selectedCapsuleUrn && activeTab === 'finder',
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Copy className="w-8 h-8 text-orange-600" />
          Redundancy Detection
        </h1>
        <p className="mt-2 text-gray-600">
          Identify duplicate and similar data capsules to reduce redundancy
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('report')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'report'
                  ? 'border-orange-600 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Redundancy Report
            </button>
            <button
              onClick={() => setActiveTab('finder')}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'finder'
                  ? 'border-orange-600 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Similarity Finder
            </button>
          </nav>
        </div>

        <div className="p-6">
          {/* Report Tab */}
          {activeTab === 'report' && (
            <ReportTab
              data={reportData}
              isLoading={isLoadingReport}
              error={reportError}
              onRefresh={refetchReport}
            />
          )}

          {/* Finder Tab */}
          {activeTab === 'finder' && (
            <FinderTab
              selectedCapsuleUrn={selectedCapsuleUrn}
              capsuleSearch={capsuleSearch}
              isDropdownOpen={isDropdownOpen}
              threshold={threshold}
              sameTypeOnly={sameTypeOnly}
              dropdownRef={dropdownRef}
              capsulesData={capsulesData}
              isLoadingCapsules={isLoadingCapsules}
              similarData={similarData}
              isLoadingSimilar={isLoadingSimilar}
              onCapsuleSelect={(urn) => {
                setSelectedCapsuleUrn(urn);
                setCapsuleSearch('');
                setIsDropdownOpen(false);
              }}
              onCapsuleClear={() => {
                setSelectedCapsuleUrn(null);
                setCapsuleSearch('');
              }}
              onSearchChange={setCapsuleSearch}
              onDropdownToggle={() => setIsDropdownOpen(!isDropdownOpen)}
              onThresholdChange={setThreshold}
              onSameTypeToggle={() => setSameTypeOnly(!sameTypeOnly)}
              onRefresh={refetchSimilar}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// Report Tab Component
function ReportTab({
  data,
  isLoading,
  error,
  onRefresh,
}: {
  data: any;
  isLoading: boolean;
  error: any;
  onRefresh: () => void;
}) {
  if (isLoading) {
    return <Loading text="Generating redundancy report..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to generate report"
        message={error?.message || 'Unknown error'}
        onRetry={onRefresh}
      />
    );
  }

  if (!data) {
    return <div className="text-center py-12 text-gray-500">No data available</div>;
  }

  const duplicateRate = data.total_capsules > 0
    ? ((data.duplicate_pairs / data.total_capsules) * 100).toFixed(1)
    : 0;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Total Capsules</span>
            <Layers className="w-4 h-4 text-gray-400" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.total_capsules}</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Duplicate Pairs</span>
            <Copy className="w-4 h-4 text-orange-600" />
          </div>
          <p className="text-3xl font-bold text-orange-600">{data.duplicate_pairs}</p>
          <p className="text-xs text-gray-500 mt-1">{duplicateRate}% of total</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Est. Savings</span>
            <TrendingDown className="w-4 h-4 text-green-600" />
          </div>
          <p className="text-3xl font-bold text-green-600">
            {data.savings_estimate?.percentage || 0}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            ~{data.savings_estimate?.capsules_to_consolidate || 0} capsules
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Confidence</span>
            <CheckCircle2 className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-blue-600">
            {data.savings_estimate?.confidence || 'Medium'}
          </p>
        </div>
      </div>

      {/* Breakdown by Layer */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Duplicates by Layer</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(data.by_layer || {}).map(([layer, count]) => (
            <div key={layer} className="border border-gray-200 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-600 capitalize">{layer}</p>
              <p className="text-2xl font-bold text-gray-900">{count as number}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Breakdown by Type */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Duplicates by Type</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(data.by_type || {}).map(([type, count]) => (
            <div key={type} className="border border-gray-200 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-600 capitalize">{type}</p>
              <p className="text-2xl font-bold text-gray-900">{count as number}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Duplicate Candidates */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            High-Confidence Duplicates ({data.potential_duplicates?.length || 0})
          </h3>
          <button
            onClick={onRefresh}
            className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700"
          >
            Refresh Report
          </button>
        </div>

        {data.potential_duplicates?.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-3" />
            <p className="text-gray-600">No high-confidence duplicates found</p>
            <p className="text-sm text-gray-500 mt-1">Your data architecture is well-organized!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.potential_duplicates?.map((pair: any, idx: number) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:border-orange-300 transition-colors">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold text-gray-900">{pair.capsule1_name}</span>
                      {pair.capsule1_layer && (
                        <Badge variant={pair.capsule1_layer} size="sm">{pair.capsule1_layer}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 font-mono">{pair.capsule1_urn}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="text-center px-4 py-2 bg-orange-100 rounded-lg">
                      <p className="text-xs text-orange-800 font-medium">Similarity</p>
                      <p className="text-lg font-bold text-orange-600">
                        {(pair.similarity_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  <div className="flex-1 text-right">
                    <div className="flex items-center gap-2 justify-end mb-2">
                      <span className="font-semibold text-gray-900">{pair.capsule2_name}</span>
                      {pair.capsule2_layer && (
                        <Badge variant={pair.capsule2_layer} size="sm">{pair.capsule2_layer}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 font-mono">{pair.capsule2_urn}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <AlertCircle className="w-4 h-4" />
                  <span>Reasons: {pair.reasons?.join(', ')}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Finder Tab Component
function FinderTab({
  selectedCapsuleUrn,
  capsuleSearch,
  isDropdownOpen,
  threshold,
  sameTypeOnly,
  dropdownRef,
  capsulesData,
  isLoadingCapsules,
  similarData,
  isLoadingSimilar,
  onCapsuleSelect,
  onCapsuleClear,
  onSearchChange,
  onDropdownToggle,
  onThresholdChange,
  onSameTypeToggle,
  onRefresh,
}: any) {
  return (
    <div className="space-y-6">
      {/* Capsule Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Capsule to Analyze
        </label>

        {selectedCapsuleUrn ? (
          <div className="flex items-center gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <span className="text-sm font-medium text-orange-900 flex-1">
              {selectedCapsuleUrn.split(':').pop()}
            </span>
            <button
              onClick={onCapsuleClear}
              className="text-orange-600 hover:text-orange-800"
              title="Clear selection"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div ref={dropdownRef} className="relative">
            <button
              type="button"
              onClick={onDropdownToggle}
              className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
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
                      onChange={(e) => onSearchChange(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      autoFocus
                    />
                  </div>
                </div>

                <div className="max-h-60 overflow-y-auto">
                  {isLoadingCapsules ? (
                    <div className="px-4 py-8 text-center text-gray-500">Loading...</div>
                  ) : capsulesData?.data && capsulesData.data.length > 0 ? (
                    capsulesData.data.map((capsule: any) => (
                      <button
                        key={capsule.urn}
                        onClick={() => onCapsuleSelect(capsule.urn)}
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

      {/* Configuration */}
      {selectedCapsuleUrn && (
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Similarity Threshold
            </label>
            <select
              value={threshold}
              onChange={(e) => onThresholdChange(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="0.5">50% (Loose)</option>
              <option value="0.6">60%</option>
              <option value="0.7">70%</option>
              <option value="0.75">75% (Default)</option>
              <option value="0.8">80%</option>
              <option value="0.9">90% (Strict)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 mt-6">
            <input
              type="checkbox"
              id="sameType"
              checked={sameTypeOnly}
              onChange={onSameTypeToggle}
              className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
            />
            <label htmlFor="sameType" className="text-sm text-gray-700">
              Same type only
            </label>
          </div>

          <button
            onClick={onRefresh}
            className="mt-6 ml-auto px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700"
          >
            Refresh
          </button>
        </div>
      )}

      {/* Results */}
      {selectedCapsuleUrn && (
        <>
          {isLoadingSimilar ? (
            <Loading text="Finding similar capsules..." />
          ) : similarData?.results.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-3" />
              <p className="text-gray-600">No similar capsules found</p>
              <p className="text-sm text-gray-500 mt-1">
                Try lowering the similarity threshold or disabling "same type only"
              </p>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Similar Capsules ({similarData?.results_count || 0})
              </h3>

              <div className="space-y-3">
                {similarData?.results.map((result: any) => (
                  <Link
                    key={result.capsule_urn}
                    href={`/capsules/${encodeURIComponent(result.capsule_urn)}`}
                    className="block border border-gray-200 rounded-lg p-4 hover:border-orange-300 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-gray-900">{result.capsule_name}</span>
                          <Badge variant={result.capsule_type} size="sm">{result.capsule_type}</Badge>
                          {result.layer && (
                            <Badge variant={result.layer} size="sm">{result.layer}</Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 font-mono">{result.capsule_urn}</p>
                      </div>

                      <div className="text-center px-4 py-2 bg-orange-100 rounded-lg">
                        <p className="text-xs text-orange-800 font-medium">Similarity</p>
                        <p className="text-2xl font-bold text-orange-600">
                          {(result.similarity.combined_score * 100).toFixed(0)}%
                        </p>
                        <p className="text-xs text-orange-700 capitalize">
                          {result.similarity.confidence}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-2 mb-3">
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <p className="text-xs text-gray-600">Name</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(result.similarity.name_score * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <p className="text-xs text-gray-600">Schema</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(result.similarity.schema_score * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <p className="text-xs text-gray-600">Lineage</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(result.similarity.lineage_score * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <p className="text-xs text-gray-600">Metadata</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(result.similarity.metadata_score * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>

                    <div className="text-sm text-gray-600">
                      <strong>Reasons:</strong> {result.reasons.join(', ')}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Help Section */}
      {!selectedCapsuleUrn && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 mb-2">How to Use Similarity Finder</h3>
          <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
            <li>Select a capsule using the search dropdown above</li>
            <li>Adjust the similarity threshold (higher = stricter matches)</li>
            <li>Optionally filter to same type only (model, source, etc.)</li>
            <li>Review similar capsules with detailed similarity scores</li>
            <li>Click on any result to view its details</li>
          </ol>
        </div>
      )}
    </div>
  );
}
