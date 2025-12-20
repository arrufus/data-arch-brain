'use client';

/**
 * Tags Page
 *
 * Browse and explore tags with their associated capsules and columns.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Tag, Search, ChevronRight, Database, Shield } from 'lucide-react';
import Link from 'next/link';

export default function TagsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  // Fetch tags list
  const { data: tagsData, isLoading, error } = useQuery({
    queryKey: ['tags-browse', searchQuery, categoryFilter],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/tags', {
        params: {
          search: searchQuery || undefined,
          category: categoryFilter || undefined,
          limit: 200,
        },
      });
      return response.data;
    },
  });

  // Fetch tag categories
  const { data: categoriesData } = useQuery({
    queryKey: ['tag-categories-browse'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/tags/categories');
      return response.data;
    },
  });

  // Fetch selected tag details
  const { data: tagDetail } = useQuery({
    queryKey: ['tag-detail', selectedTag],
    queryFn: async () => {
      if (!selectedTag) return null;
      const response = await apiClient.get(`/api/v1/tags/${selectedTag}`);
      return response.data;
    },
    enabled: !!selectedTag,
  });

  // Fetch capsules with selected tag
  const { data: capsulesData } = useQuery({
    queryKey: ['tag-capsules', selectedTag],
    queryFn: async () => {
      if (!selectedTag) return null;
      const response = await apiClient.get(`/api/v1/tags/${selectedTag}/capsules`, {
        params: { limit: 100 },
      });
      return response.data;
    },
    enabled: !!selectedTag,
  });

  // Fetch columns with selected tag
  const { data: columnsData } = useQuery({
    queryKey: ['tag-columns', selectedTag],
    queryFn: async () => {
      if (!selectedTag) return null;
      const response = await apiClient.get(`/api/v1/tags/${selectedTag}/columns`, {
        params: { limit: 100 },
      });
      return response.data;
    },
    enabled: !!selectedTag,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load tags</p>
        </div>
      </div>
    );
  }

  const tags = tagsData?.data || [];
  const categories = categoriesData?.categories || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <Tag className="w-6 h-6 text-gray-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tags</h1>
            <p className="text-sm text-gray-500">
              Browse tags and view their associated capsules and columns
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{tags.length}</div>
            <div className="text-sm text-gray-500">Total Tags</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{categories.length}</div>
            <div className="text-sm text-gray-500">Categories</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Tags List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200">
              {/* Search and Filters */}
              <div className="p-4 border-b border-gray-200 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search tags..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat: string) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Tags Grid */}
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {tags.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Tag className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p>No tags found</p>
                  </div>
                ) : (
                  tags.map((tag: any) => (
                    <button
                      key={tag.id}
                      onClick={() => setSelectedTag(tag.id)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                        selectedTag === tag.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {tag.color && (
                              <div
                                className="w-3 h-3 rounded flex-shrink-0"
                                style={{ backgroundColor: tag.color }}
                              />
                            )}
                            <span className="font-medium text-gray-900 truncate">{tag.name}</span>
                          </div>
                          {tag.description && (
                            <p className="text-sm text-gray-500 line-clamp-2">{tag.description}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            {tag.category && (
                              <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                                {tag.category}
                              </span>
                            )}
                            {tag.sensitivity_level && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                <Shield className="w-3 h-3" />
                                {tag.sensitivity_level}
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Tag Details */}
          <div className="lg:col-span-2">
            {!selectedTag ? (
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <Tag className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Tag</h3>
                <p className="text-gray-500">
                  Choose a tag from the list to view its details and associated items
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Tag Details */}
                {tagDetail && (
                  <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-start gap-3 mb-4">
                      {tagDetail.color && (
                        <div
                          className="w-8 h-8 rounded flex-shrink-0"
                          style={{ backgroundColor: tagDetail.color }}
                        />
                      )}
                      <div className="flex-1">
                        <h2 className="text-xl font-bold text-gray-900 mb-1">{tagDetail.name}</h2>
                        {tagDetail.description && (
                          <p className="text-gray-600">{tagDetail.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {tagDetail.category && (
                        <div>
                          <div className="text-sm text-gray-500">Category</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {tagDetail.category}
                          </div>
                        </div>
                      )}
                      {tagDetail.sensitivity_level && (
                        <div>
                          <div className="text-sm text-gray-500">Sensitivity</div>
                          <div className="text-lg font-semibold text-gray-900 capitalize">
                            {tagDetail.sensitivity_level}
                          </div>
                        </div>
                      )}
                      <div>
                        <div className="text-sm text-gray-500">Created</div>
                        <div className="text-sm text-gray-900">
                          {new Date(tagDetail.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>

                    {tagDetail.meta && Object.keys(tagDetail.meta).length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="text-sm font-medium text-gray-700 mb-2">Metadata:</div>
                        <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded-lg overflow-x-auto">
                          {JSON.stringify(tagDetail.meta, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {/* Associated Capsules */}
                {capsulesData && (
                  <div className="bg-white rounded-lg border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h3 className="text-lg font-semibold text-gray-900">Tagged Capsules</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {capsulesData.length} capsule(s) with this tag
                      </p>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {capsulesData.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                          <p>No capsules tagged</p>
                        </div>
                      ) : (
                        capsulesData.map((item: any) => (
                          <Link
                            key={item.capsule_id}
                            href={`/capsules/${encodeURIComponent(item.capsule_urn)}`}
                            className="block p-4 hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <Database className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                  <span className="font-medium text-gray-900 truncate">
                                    {item.capsule_name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                                    {item.capsule_type}
                                  </span>
                                  {item.added_by && (
                                    <span className="text-xs text-gray-500">by {item.added_by}</span>
                                  )}
                                  <span className="text-xs text-gray-500">
                                    {new Date(item.added_at).toLocaleDateString()}
                                  </span>
                                </div>
                              </div>
                              <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                            </div>
                          </Link>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* Associated Columns */}
                {columnsData && (
                  <div className="bg-white rounded-lg border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h3 className="text-lg font-semibold text-gray-900">Tagged Columns</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {columnsData.length} column(s) with this tag
                      </p>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {columnsData.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                          <p>No columns tagged</p>
                        </div>
                      ) : (
                        <div className="max-h-96 overflow-y-auto">
                          {columnsData.map((item: any) => (
                            <div
                              key={item.column_id}
                              className="p-4 hover:bg-gray-50 transition-colors"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-medium text-gray-900 truncate">
                                      {item.column_name}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-500">in</span>
                                    <Link
                                      href={`/capsules/${encodeURIComponent(item.capsule_name)}`}
                                      className="text-sm text-blue-600 hover:text-blue-700 underline"
                                    >
                                      {item.capsule_name}
                                    </Link>
                                    {item.added_by && (
                                      <span className="text-xs text-gray-500">by {item.added_by}</span>
                                    )}
                                    <span className="text-xs text-gray-500">
                                      {new Date(item.added_at).toLocaleDateString()}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
