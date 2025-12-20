'use client';

/**
 * Data Products Page
 *
 * Browse and explore data products with their associated capsules and SLO status.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Package, Search, ChevronRight, Database, User, AlertCircle, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function ProductsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);

  // Fetch products list
  const { data: productsData, isLoading, error } = useQuery({
    queryKey: ['products-list', searchQuery, statusFilter],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/products', {
        params: {
          search: searchQuery || undefined,
          status: statusFilter || undefined,
          limit: 100,
        },
      });
      return response.data;
    },
  });

  // Fetch product stats
  const { data: statsData } = useQuery({
    queryKey: ['products-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/products/stats');
      return response.data;
    },
  });

  // Fetch selected product details
  const { data: productDetail } = useQuery({
    queryKey: ['product-detail', selectedProduct],
    queryFn: async () => {
      if (!selectedProduct) return null;
      const response = await apiClient.get(`/api/v1/products/${selectedProduct}`);
      return response.data;
    },
    enabled: !!selectedProduct,
  });

  // Fetch SLO status for selected product
  const { data: sloStatus } = useQuery({
    queryKey: ['product-slo', selectedProduct],
    queryFn: async () => {
      if (!selectedProduct) return null;
      const response = await apiClient.get(`/api/v1/products/${selectedProduct}/slo-status`);
      return response.data;
    },
    enabled: !!selectedProduct,
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
          <p className="text-red-800">Failed to load data products</p>
        </div>
      </div>
    );
  }

  const products = productsData?.data || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <Package className="w-6 h-6 text-gray-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Products</h1>
            <p className="text-sm text-gray-500">
              Manage data products and their service level objectives
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {statsData && (
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">{statsData.total_products}</div>
              <div className="text-sm text-gray-500">Total Products</div>
            </div>
            {statsData.by_status && (
              <>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {statsData.by_status.active || 0}
                  </div>
                  <div className="text-sm text-gray-500">Active</div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {statsData.by_status.draft || 0}
                  </div>
                  <div className="text-sm text-gray-500">Draft</div>
                </div>
              </>
            )}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">
                {statsData.total_capsule_associations || 0}
              </div>
              <div className="text-sm text-gray-500">Total Capsules</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Products List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200">
              {/* Search and Filters */}
              <div className="p-4 border-b border-gray-200 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search products..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Statuses</option>
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="deprecated">Deprecated</option>
                </select>
              </div>

              {/* Products List */}
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {products.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Package className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p>No products found</p>
                  </div>
                ) : (
                  products.map((product: any) => (
                    <button
                      key={product.id}
                      onClick={() => setSelectedProduct(product.id)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                        selectedProduct === product.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Package className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <span className="font-medium text-gray-900 truncate">
                              {product.name}
                            </span>
                          </div>
                          {product.description && (
                            <p className="text-sm text-gray-500 line-clamp-2">{product.description}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                                product.status === 'active'
                                  ? 'bg-green-100 text-green-800'
                                  : product.status === 'draft'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {product.status}
                            </span>
                            {product.version && (
                              <span className="text-xs text-gray-500">v{product.version}</span>
                            )}
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {product.capsule_count} capsules
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

          {/* Right Panel - Product Details */}
          <div className="lg:col-span-2">
            {!selectedProduct ? (
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <Package className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Data Product</h3>
                <p className="text-gray-500">
                  Choose a product from the list to view its details, capsules, and SLO status
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Product Details */}
                {productDetail && (
                  <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h2 className="text-xl font-bold text-gray-900">
                            {productDetail.name}
                          </h2>
                          <span
                            className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                              productDetail.status === 'active'
                                ? 'bg-green-100 text-green-800'
                                : productDetail.status === 'draft'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {productDetail.status}
                          </span>
                          {productDetail.version && (
                            <span className="text-sm text-gray-500">v{productDetail.version}</span>
                          )}
                        </div>
                        {productDetail.description && (
                          <p className="text-gray-600 mb-3">{productDetail.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-500">Capsules</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {productDetail.capsule_count}
                        </div>
                      </div>
                      {productDetail.domain_name && (
                        <div>
                          <div className="text-sm text-gray-500">Domain</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {productDetail.domain_name}
                          </div>
                        </div>
                      )}
                      {productDetail.owner_name && (
                        <div>
                          <div className="text-sm text-gray-500">Owner</div>
                          <div className="text-lg font-semibold text-gray-900">
                            {productDetail.owner_name}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* SLO Configuration */}
                    {productDetail.slo && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <h3 className="text-sm font-medium text-gray-900 mb-3">
                          Service Level Objectives
                        </h3>
                        <div className="grid grid-cols-3 gap-4">
                          {productDetail.slo.freshness_hours && (
                            <div>
                              <div className="text-sm text-gray-500">Freshness</div>
                              <div className="text-sm font-medium text-gray-900">
                                {productDetail.slo.freshness_hours}h
                              </div>
                            </div>
                          )}
                          {productDetail.slo.availability_percent && (
                            <div>
                              <div className="text-sm text-gray-500">Availability</div>
                              <div className="text-sm font-medium text-gray-900">
                                {productDetail.slo.availability_percent}%
                              </div>
                            </div>
                          )}
                          {productDetail.slo.quality_threshold && (
                            <div>
                              <div className="text-sm text-gray-500">Quality</div>
                              <div className="text-sm font-medium text-gray-900">
                                {(productDetail.slo.quality_threshold * 100).toFixed(0)}%
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Tags */}
                    {productDetail.tags && productDetail.tags.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="text-sm font-medium text-gray-700 mb-2">Tags:</div>
                        <div className="flex flex-wrap gap-2">
                          {productDetail.tags.map((tag: string) => (
                            <span
                              key={tag}
                              className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* SLO Status */}
                {sloStatus && (
                  <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">SLO Compliance</h3>
                    <div
                      className={`flex items-center gap-3 p-4 rounded-lg mb-4 ${
                        sloStatus.overall_status === 'passing'
                          ? 'bg-green-50 border border-green-200'
                          : sloStatus.overall_status === 'warning'
                          ? 'bg-yellow-50 border border-yellow-200'
                          : 'bg-red-50 border border-red-200'
                      }`}
                    >
                      {sloStatus.overall_status === 'passing' ? (
                        <CheckCircle className="w-6 h-6 text-green-600" />
                      ) : (
                        <AlertCircle className="w-6 h-6 text-yellow-600" />
                      )}
                      <div>
                        <div className="font-medium text-gray-900 capitalize">
                          {sloStatus.overall_status}
                        </div>
                        <div className="text-sm text-gray-600">
                          Last checked: {new Date(sloStatus.checked_at).toLocaleString()}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {sloStatus.freshness && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-700">Freshness</span>
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-medium ${
                              sloStatus.freshness.status === 'passing'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {sloStatus.freshness.status}
                          </span>
                        </div>
                      )}
                      {sloStatus.availability && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-700">Availability</span>
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-medium ${
                              sloStatus.availability.status === 'passing'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {sloStatus.availability.status}
                          </span>
                        </div>
                      )}
                      {sloStatus.quality && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-700">Quality</span>
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-medium ${
                              sloStatus.quality.status === 'passing'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {sloStatus.quality.status}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Capsules in Product */}
                {productDetail && productDetail.capsules && (
                  <div className="bg-white rounded-lg border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h3 className="text-lg font-semibold text-gray-900">Associated Capsules</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {productDetail.capsules.length} capsule(s) in this product
                      </p>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {productDetail.capsules.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                          <p>No capsules associated with this product</p>
                        </div>
                      ) : (
                        productDetail.capsules.map((capsule: any) => (
                          <Link
                            key={capsule.capsule_id}
                            href={`/capsules/${encodeURIComponent(capsule.capsule_urn)}`}
                            className="block p-4 hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <Database className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                  <span className="font-medium text-gray-900 truncate">
                                    {capsule.capsule_name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    {capsule.role}
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    Added {new Date(capsule.added_at).toLocaleDateString()}
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
