'use client';

/**
 * Domains Page
 *
 * Browse and explore business domains with their associated data capsules.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { FolderTree, Search, ChevronRight, Database, User } from 'lucide-react';
import Link from 'next/link';

export default function DomainsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [rootOnly, setRootOnly] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  // Fetch domains list
  const { data: domainsData, isLoading, error } = useQuery({
    queryKey: ['domains-list', searchQuery, rootOnly],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/domains', {
        params: {
          search: searchQuery || undefined,
          root_only: rootOnly,
          limit: 100,
        },
      });
      return response.data;
    },
  });

  // Fetch domain stats
  const { data: statsData } = useQuery({
    queryKey: ['domains-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/domains/stats');
      return response.data;
    },
  });

  // Fetch selected domain details
  const { data: domainDetail } = useQuery({
    queryKey: ['domain-detail', selectedDomain],
    queryFn: async () => {
      if (!selectedDomain) return null;
      const response = await apiClient.get(`/api/v1/domains/${encodeURIComponent(selectedDomain)}`);
      return response.data;
    },
    enabled: !!selectedDomain,
  });

  // Fetch capsules for selected domain
  const { data: capsulesData } = useQuery({
    queryKey: ['domain-capsules', selectedDomain],
    queryFn: async () => {
      if (!selectedDomain) return null;
      const response = await apiClient.get(
        `/api/v1/domains/${encodeURIComponent(selectedDomain)}/capsules`,
        { params: { limit: 100 } }
      );
      return response.data;
    },
    enabled: !!selectedDomain,
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
          <p className="text-red-800">Failed to load domains</p>
        </div>
      </div>
    );
  }

  const domains = domainsData?.data || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <FolderTree className="w-6 h-6 text-gray-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Business Domains</h1>
            <p className="text-sm text-gray-500">
              Explore organizational domains and their data capsules
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {statsData && (
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">{statsData.total_domains}</div>
              <div className="text-sm text-gray-500">Total Domains</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">{statsData.root_domains}</div>
              <div className="text-sm text-gray-500">Root Domains</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">
                {Object.keys(statsData.capsules_by_domain || {}).length}
              </div>
              <div className="text-sm text-gray-500">Domains with Capsules</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Domains List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200">
              {/* Search and Filters */}
              <div className="p-4 border-b border-gray-200 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search domains..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rootOnly}
                    onChange={(e) => setRootOnly(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span>Root domains only</span>
                </label>
              </div>

              {/* Domains List */}
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {domains.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <FolderTree className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p>No domains found</p>
                  </div>
                ) : (
                  domains.map((domain: any) => (
                    <button
                      key={domain.id}
                      onClick={() => setSelectedDomain(domain.name)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                        selectedDomain === domain.name ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <FolderTree className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <span className="font-medium text-gray-900 truncate">
                              {domain.name}
                            </span>
                          </div>
                          {domain.description && (
                            <p className="text-sm text-gray-500 line-clamp-2">{domain.description}</p>
                          )}
                          <div className="flex items-center gap-3 mt-2">
                            {domain.owner_name && (
                              <span className="text-xs text-gray-500 flex items-center gap-1">
                                <User className="w-3 h-3" />
                                {domain.owner_name}
                              </span>
                            )}
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {domain.capsule_count} capsules
                            </span>
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

          {/* Right Panel - Domain Details */}
          <div className="lg:col-span-2">
            {!selectedDomain ? (
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <FolderTree className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Domain</h3>
                <p className="text-gray-500">
                  Choose a domain from the list to view its details and associated capsules
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Domain Details */}
                {domainDetail && (
                  <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h2 className="text-xl font-bold text-gray-900 mb-1">
                          {domainDetail.name}
                        </h2>
                        {domainDetail.description && (
                          <p className="text-gray-600">{domainDetail.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                      <div>
                        <div className="text-sm text-gray-500">Capsules</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {domainDetail.capsule_count}
                        </div>
                      </div>
                      {domainDetail.owner_name && (
                        <div>
                          <div className="text-sm text-gray-500">Owner</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {domainDetail.owner_name}
                          </div>
                        </div>
                      )}
                      {domainDetail.parent_id && (
                        <div>
                          <div className="text-sm text-gray-500">Parent Domain</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {domainDetail.parent_id}
                          </div>
                        </div>
                      )}
                      {domainDetail.child_domains && domainDetail.child_domains.length > 0 && (
                        <div>
                          <div className="text-sm text-gray-500">Child Domains</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {domainDetail.child_domains.length}
                          </div>
                        </div>
                      )}
                    </div>

                    {domainDetail.child_domains && domainDetail.child_domains.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="text-sm font-medium text-gray-700 mb-2">
                          Child Domains:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {domainDetail.child_domains.map((child: string) => (
                            <button
                              key={child}
                              onClick={() => setSelectedDomain(child)}
                              className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm transition-colors"
                            >
                              {child}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Capsules in Domain */}
                {capsulesData && (
                  <div className="bg-white rounded-lg border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h3 className="text-lg font-semibold text-gray-900">Data Capsules</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {capsulesData.capsules?.length || 0} capsules in this domain
                      </p>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {!capsulesData.capsules || capsulesData.capsules.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                          <p>No capsules in this domain</p>
                        </div>
                      ) : (
                        capsulesData.capsules.map((capsule: any) => (
                          <Link
                            key={capsule.id}
                            href={`/capsules/${encodeURIComponent(capsule.urn)}`}
                            className="block p-4 hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <Database className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                  <span className="font-medium text-gray-900 truncate">
                                    {capsule.name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span
                                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                                      capsule.layer === 'gold'
                                        ? 'bg-yellow-100 text-yellow-800'
                                        : capsule.layer === 'silver'
                                        ? 'bg-slate-100 text-slate-800'
                                        : 'bg-amber-100 text-amber-800'
                                    }`}
                                  >
                                    {capsule.layer}
                                  </span>
                                  <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                                    {capsule.capsule_type}
                                  </span>
                                  {capsule.has_pii && (
                                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                      PII
                                    </span>
                                  )}
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
