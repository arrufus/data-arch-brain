'use client';

/**
 * Interactive Lineage Graph Page
 *
 * Visual exploration of data lineage using React Flow.
 */

import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { GitBranch, X, ChevronDown, Search } from 'lucide-react';
import LineageGraph from '@/components/lineage/LineageGraph';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export default function LineagePage() {
  const searchParams = useSearchParams();
  const [layoutDirection, setLayoutDirection] = useState<'TB' | 'LR'>('TB');
  const [selectedCapsuleUrn, setSelectedCapsuleUrn] = useState<string | null>(null);
  const [capsuleSearch, setCapsuleSearch] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get capsule URN from URL query params if present
  useEffect(() => {
    const urnFromUrl = searchParams.get('capsule');
    if (urnFromUrl) {
      setSelectedCapsuleUrn(urnFromUrl);
    }
  }, [searchParams]);

  // Handle click outside to close dropdown
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

  // Fetch capsules for type-ahead dropdown
  const { data: capsulesData, isLoading: isLoadingCapsules } = useQuery({
    queryKey: ['capsules-search', capsuleSearch],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/capsules', {
        params: {
          search: capsuleSearch || undefined,
          limit: capsuleSearch ? 10 : 20, // Show more when not filtering
        },
      });
      return response.data;
    },
    enabled: isDropdownOpen, // Fetch when dropdown is open
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <GitBranch className="w-8 h-8 text-blue-600" />
          Interactive Lineage Graph
        </h1>
        <p className="mt-2 text-gray-600">
          Explore data flow and dependencies with an interactive graph visualization
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        {/* Capsule Filter - Type-ahead Dropdown */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Focus on Capsule (optional)
          </label>
          {selectedCapsuleUrn ? (
            <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <span className="text-sm font-medium text-blue-900 flex-1">
                {selectedCapsuleUrn.split(':').pop()}
              </span>
              <button
                onClick={() => {
                  setSelectedCapsuleUrn(null);
                  setCapsuleSearch('');
                }}
                className="text-blue-600 hover:text-blue-800"
                title="Clear selection"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div ref={dropdownRef} className="relative">
              {/* Dropdown Button */}
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <span className="text-gray-500">
                  {capsuleSearch || 'Select a capsule...'}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu */}
              {isDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                  {/* Search Input */}
                  <div className="p-2 border-b border-gray-200">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Type to search..."
                        value={capsuleSearch}
                        onChange={(e) => setCapsuleSearch(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        autoFocus
                      />
                    </div>
                  </div>

                  {/* Results List */}
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

        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Layout Direction */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Layout:</label>
            <select
              value={layoutDirection}
              onChange={(e) => setLayoutDirection(e.target.value as 'TB' | 'LR')}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="TB">Top to Bottom</option>
              <option value="LR">Left to Right</option>
            </select>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span>Model</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Source</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span>Seed</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-orange-500" />
              <span>Snapshot</span>
            </div>
          </div>
        </div>
      </div>

      {/* Graph Container */}
      <div className="bg-white rounded-lg shadow overflow-hidden" style={{ height: 'calc(100vh - 300px)' }}>
        <LineageGraph
          focusedCapsuleUrn={selectedCapsuleUrn}
          layoutDirection={layoutDirection}
        />
      </div>

      {/* Legend & Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">Graph Controls</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Pan:</strong> Click and drag the background</li>
          <li>• <strong>Zoom:</strong> Use mouse wheel or pinch gesture</li>
          <li>• <strong>Select Node:</strong> Click on a capsule to view details</li>
          <li>• <strong>Follow Edge:</strong> Click on an edge to see transformation details</li>
        </ul>
      </div>
    </div>
  );
}
