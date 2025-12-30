'use client';

/**
 * Column Search Component (Phase 7)
 *
 * Search and filter columns to navigate to lineage views
 */

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useColumnSearch } from '@/lib/api/column-lineage';
import {
  Search,
  Filter,
  X,
  Database,
  Tag,
  Shield,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
} from 'lucide-react';

interface ColumnSearchProps {
  defaultSearch?: string;
  onSelectColumn?: (columnUrn: string) => void;
}

export default function ColumnSearch({ defaultSearch = '', onSelectColumn }: ColumnSearchProps) {
  const router = useRouter();

  // Search state
  const [searchInput, setSearchInput] = useState(defaultSearch);
  const [debouncedSearch, setDebouncedSearch] = useState(defaultSearch);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [semanticTypeFilter, setSemanticTypeFilter] = useState<string>('');
  const [piiTypeFilter, setPiiTypeFilter] = useState<string>('');
  const [capsuleFilter, setCapsuleFilter] = useState<string>('');

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build search options
  const searchOptions = useMemo(() => {
    const options: any = {};

    if (debouncedSearch) options.search = debouncedSearch;
    if (semanticTypeFilter) options.semantic_type = semanticTypeFilter;
    if (piiTypeFilter) options.pii_type = piiTypeFilter;
    if (capsuleFilter) options.capsule_urn = capsuleFilter;

    return options;
  }, [debouncedSearch, semanticTypeFilter, piiTypeFilter, capsuleFilter]);

  // Fetch search results
  const { data, isLoading, error } = useColumnSearch(searchOptions);

  const hasActiveFilters = !!(semanticTypeFilter || piiTypeFilter || capsuleFilter);
  const hasResults = data && data.data.length > 0;
  const showResults = debouncedSearch || hasActiveFilters;

  const handleSelectColumn = (columnUrn: string) => {
    if (onSelectColumn) {
      onSelectColumn(columnUrn);
    } else {
      router.push(`/lineage/columns/${encodeURIComponent(columnUrn)}`);
    }
  };

  const handleClearFilters = () => {
    setSemanticTypeFilter('');
    setPiiTypeFilter('');
    setCapsuleFilter('');
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Search Input */}
      <div className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-4 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search columns by name..."
            className="w-full pl-12 pr-12 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput('')}
              className="absolute right-4 p-1 hover:bg-gray-100 rounded transition-colors"
              title="Clear search"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>

        {/* Filter Toggle Button */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`
            mt-2 px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors
            ${
              showFilters || hasActiveFilters
                ? 'bg-blue-50 text-blue-700 border-2 border-blue-300'
                : 'bg-gray-100 text-gray-700 border-2 border-transparent hover:bg-gray-200'
            }
          `}
        >
          <Filter className="w-4 h-4" />
          Filters
          {hasActiveFilters && (
            <span className="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
              {[semanticTypeFilter, piiTypeFilter, capsuleFilter].filter(Boolean).length}
            </span>
          )}
          {showFilters ? (
            <ChevronUp className="w-4 h-4 ml-auto" />
          ) : (
            <ChevronDown className="w-4 h-4 ml-auto" />
          )}
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="mt-3 p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-900">Filter Columns</h3>
            {hasActiveFilters && (
              <button
                onClick={handleClearFilters}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Semantic Type Filter */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <Database className="w-4 h-4" />
                Semantic Type
              </label>
              <select
                value={semanticTypeFilter}
                onChange={(e) => setSemanticTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All types</option>
                <option value="identifier">Identifier</option>
                <option value="measure">Measure</option>
                <option value="dimension">Dimension</option>
                <option value="timestamp">Timestamp</option>
                <option value="foreign_key">Foreign Key</option>
                <option value="primary_key">Primary Key</option>
              </select>
            </div>

            {/* PII Type Filter */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <Shield className="w-4 h-4" />
                PII Type
              </label>
              <select
                value={piiTypeFilter}
                onChange={(e) => setPiiTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All (including non-PII)</option>
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="ssn">SSN</option>
                <option value="credit_card">Credit Card</option>
                <option value="name">Name</option>
                <option value="address">Address</option>
                <option value="ip_address">IP Address</option>
              </select>
            </div>

            {/* Capsule Filter */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                <Tag className="w-4 h-4" />
                Capsule
              </label>
              <input
                type="text"
                value={capsuleFilter}
                onChange={(e) => setCapsuleFilter(e.target.value)}
                placeholder="Capsule URN or name"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {showResults && (
        <div className="mt-4 bg-white border border-gray-200 rounded-lg shadow-lg max-h-[500px] overflow-y-auto">
          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center p-12">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
                <p className="text-sm text-gray-600">Searching columns...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-6">
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-red-900 mb-1">Search failed</h3>
                  <p className="text-sm text-red-700">
                    {error instanceof Error ? error.message : 'An unknown error occurred'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Results List */}
          {!isLoading && !error && hasResults && (
            <>
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <p className="text-sm text-gray-600">
                  Found <strong>{data.pagination.total}</strong> column
                  {data.pagination.total !== 1 ? 's' : ''}
                  {data.pagination.has_more && ' (showing first 20)'}
                </p>
              </div>
              <div className="divide-y divide-gray-200">
                {data.data.map((column) => (
                  <button
                    key={column.urn}
                    onClick={() => handleSelectColumn(column.urn)}
                    className="w-full p-4 hover:bg-gray-50 transition-colors text-left"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {column.name}
                          </h3>
                          {column.pii_type && (
                            <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded border border-red-300">
                              PII: {column.pii_type}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <span className="truncate">{column.capsule_name}</span>
                          {column.layer && (
                            <>
                              <span>•</span>
                              <span className="uppercase">{column.layer}</span>
                            </>
                          )}
                          {column.data_type && (
                            <>
                              <span>•</span>
                              <span className="font-mono">{column.data_type}</span>
                            </>
                          )}
                        </div>
                        {column.description && (
                          <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                            {column.description}
                          </p>
                        )}
                      </div>
                      {column.semantic_type && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded flex-shrink-0">
                          {column.semantic_type}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Empty State */}
          {!isLoading && !error && !hasResults && (
            <div className="p-12 text-center">
              <Search className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-sm font-medium text-gray-900 mb-1">No columns found</h3>
              <p className="text-sm text-gray-600">
                Try adjusting your search or filters
              </p>
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      {!showResults && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Tip:</strong> Search for columns by name, or use filters to find columns by
            semantic type, PII classification, or capsule. Click on any result to view its lineage
            graph.
          </p>
        </div>
      )}
    </div>
  );
}
