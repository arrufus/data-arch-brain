'use client';

/**
 * Capsule Filters Component
 *
 * Filter controls for capsule browser (search, layer, type, PII).
 */

import { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { CapsuleFilters as CapsuleFiltersType } from '@/lib/api/types';

interface CapsuleFiltersProps {
  filters: CapsuleFiltersType;
  onFiltersChange: (filters: CapsuleFiltersType) => void;
}

export default function CapsuleFilters({ filters, onFiltersChange }: CapsuleFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search || '');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== filters.search) {
        onFiltersChange({ ...filters, search: searchInput || undefined, offset: 0 });
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [searchInput]);

  const handleLayerChange = (layer: string) => {
    onFiltersChange({
      ...filters,
      layer: layer ? (layer as any) : undefined,
      offset: 0,
    });
  };

  const handleTypeChange = (type: string) => {
    onFiltersChange({
      ...filters,
      capsule_type: type ? (type as any) : undefined,
      offset: 0,
    });
  };

  const handlePIIChange = (hasPII: string) => {
    onFiltersChange({
      ...filters,
      has_pii: hasPII === 'true' ? true : hasPII === 'false' ? false : undefined,
      offset: 0,
    });
  };

  const handleClearFilters = () => {
    setSearchInput('');
    onFiltersChange({
      offset: 0,
      limit: filters.limit,
    });
  };

  const hasActiveFilters = !!(
    filters.search ||
    filters.layer ||
    filters.capsule_type ||
    filters.has_pii !== undefined
  );

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search capsules by name, description, or URN..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Filter Dropdowns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Layer Filter */}
        <div>
          <label htmlFor="layer-filter" className="block text-sm font-medium text-gray-700 mb-1">
            Layer
          </label>
          <select
            id="layer-filter"
            value={filters.layer || ''}
            onChange={(e) => handleLayerChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Layers</option>
            <option value="raw">Raw</option>
            <option value="bronze">Bronze</option>
            <option value="silver">Silver</option>
            <option value="gold">Gold</option>
            <option value="marts">Marts</option>
          </select>
        </div>

        {/* Type Filter */}
        <div>
          <label htmlFor="type-filter" className="block text-sm font-medium text-gray-700 mb-1">
            Capsule Type
          </label>
          <select
            id="type-filter"
            value={filters.capsule_type || ''}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Types</option>
            <option value="model">Model</option>
            <option value="source">Source</option>
            <option value="seed">Seed</option>
            <option value="snapshot">Snapshot</option>
            <option value="analysis">Analysis</option>
          </select>
        </div>

        {/* PII Filter */}
        <div>
          <label htmlFor="pii-filter" className="block text-sm font-medium text-gray-700 mb-1">
            PII Status
          </label>
          <select
            id="pii-filter"
            value={
              filters.has_pii === true ? 'true' : filters.has_pii === false ? 'false' : ''
            }
            onChange={(e) => handlePIIChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All</option>
            <option value="true">Has PII</option>
            <option value="false">No PII</option>
          </select>
        </div>
      </div>

      {/* Clear Filters Button */}
      {hasActiveFilters && (
        <div className="flex justify-end">
          <button
            onClick={handleClearFilters}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
            Clear Filters
          </button>
        </div>
      )}
    </div>
  );
}
