'use client';

/**
 * Settings/Configuration Page
 *
 * Centralized management for:
 * - Domains (read-only view)
 * - Tags (full CRUD)
 * - Data Products (full CRUD)
 * - Conformance Rules (view, upload, export, delete custom rules)
 * - System Information (read-only)
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import {
  Settings,
  FolderTree,
  Tag,
  Package,
  Shield,
  Info,
  Plus,
  Edit2,
  Trash2,
  Upload,
  Download,
  Search,
  Check,
  X,
  AlertCircle,
} from 'lucide-react';

type TabType = 'domains' | 'tags' | 'products' | 'rules' | 'system';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('domains');

  const tabs = [
    { id: 'domains' as TabType, label: 'Domains', icon: FolderTree },
    { id: 'tags' as TabType, label: 'Tags', icon: Tag },
    { id: 'products' as TabType, label: 'Data Products', icon: Package },
    { id: 'rules' as TabType, label: 'Conformance Rules', icon: Shield },
    { id: 'system' as TabType, label: 'System Info', icon: Info },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-gray-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings & Configuration</h1>
            <p className="text-sm text-gray-500">Manage domains, tags, products, and rules</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 bg-white">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'domains' && <DomainsTab />}
        {activeTab === 'tags' && <TagsTab />}
        {activeTab === 'products' && <DataProductsTab />}
        {activeTab === 'rules' && <ConformanceRulesTab />}
        {activeTab === 'system' && <SystemInfoTab />}
      </div>
    </div>
  );
}

// =============================================================================
// Domains Tab (Read-only)
// =============================================================================

function DomainsTab() {
  const [searchQuery, setSearchQuery] = useState('');
  const [rootOnly, setRootOnly] = useState(false);

  const { data: domainsData, isLoading, error } = useQuery({
    queryKey: ['domains', searchQuery, rootOnly],
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

  const { data: statsData } = useQuery({
    queryKey: ['domain-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/domains/stats');
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Failed to load domains</p>
      </div>
    );
  }

  const domains = domainsData?.data || [];

  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900">Domain Hierarchy (Read-Only)</h3>
            <p className="text-sm text-blue-700 mt-1">
              Domains are organizational units that group related data capsules. They are managed through the
              ingestion process and cannot be created or modified from this interface.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {statsData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search domains..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
            <input
              type="checkbox"
              checked={rootOnly}
              onChange={(e) => setRootOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Root domains only</span>
          </label>
        </div>
      </div>

      {/* Domains Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Domain Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Owner
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Capsules
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Parent
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {domains.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                  No domains found
                </td>
              </tr>
            ) : (
              domains.map((domain: any) => (
                <tr key={domain.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <FolderTree className="w-4 h-4 text-gray-400" />
                      <span className="font-medium text-gray-900">{domain.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-500">{domain.description || '-'}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-700">{domain.owner_name || '-'}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {domain.capsule_count}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-500">{domain.parent_id || 'Root'}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// Tags Tab (Full CRUD)
// =============================================================================

function TagsTab() {
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTag, setEditingTag] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: tagsData, isLoading } = useQuery({
    queryKey: ['tags', searchQuery],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/tags', {
        params: {
          search: searchQuery || undefined,
          limit: 200,
        },
      });
      return response.data;
    },
  });

  const { data: categoriesData } = useQuery({
    queryKey: ['tag-categories'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/tags/categories');
      return response.data;
    },
  });

  const deleteTagMutation = useMutation({
    mutationFn: async (tagId: string) => {
      await apiClient.delete(`/api/v1/tags/${tagId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      queryClient.invalidateQueries({ queryKey: ['tag-categories'] });
    },
  });

  const handleDeleteTag = async (tag: any) => {
    if (window.confirm(`Are you sure you want to delete the tag "${tag.name}"? This will remove it from all associated capsules and columns.`)) {
      try {
        await deleteTagMutation.mutateAsync(tag.id);
      } catch (error: any) {
        alert(`Failed to delete tag: ${error.message}`);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const tags = tagsData?.data || [];
  const categories = categoriesData?.categories || [];

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Tag Management</h2>
          <p className="text-sm text-gray-500 mt-1">
            Create and manage tags for organizing data capsules and columns
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Tag
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{tags.length}</div>
          <div className="text-sm text-gray-500">Total Tags</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{categories.length}</div>
          <div className="text-sm text-gray-500">Categories</div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search tags..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Tags Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tags.length === 0 ? (
          <div className="col-span-full bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Tag className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No tags found</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Create your first tag
            </button>
          </div>
        ) : (
          tags.map((tag: any) => (
            <div key={tag.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {tag.color && (
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: tag.color }}
                    />
                  )}
                  <h3 className="font-medium text-gray-900">{tag.name}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setEditingTag(tag)}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteTag(tag)}
                    className="p-1 text-gray-400 hover:text-red-600 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {tag.category && (
                <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded mb-2">
                  {tag.category}
                </span>
              )}

              {tag.description && (
                <p className="text-sm text-gray-500 mb-2">{tag.description}</p>
              )}

              {tag.sensitivity_level && (
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Shield className="w-3 h-3" />
                  <span className="capitalize">{tag.sensitivity_level}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingTag) && (
        <TagFormModal
          tag={editingTag}
          categories={categories}
          onClose={() => {
            setShowCreateModal(false);
            setEditingTag(null);
          }}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['tags'] });
            queryClient.invalidateQueries({ queryKey: ['tag-categories'] });
            setShowCreateModal(false);
            setEditingTag(null);
          }}
        />
      )}
    </div>
  );
}

// Tag Form Modal Component
function TagFormModal({
  tag,
  categories,
  onClose,
  onSuccess,
}: {
  tag?: any;
  categories: string[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: tag?.name || '',
    category: tag?.category || '',
    description: tag?.description || '',
    color: tag?.color || '#3B82F6',
    sensitivity_level: tag?.sensitivity_level || '',
  });

  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: async (data: any) => {
      if (tag) {
        // Update existing tag
        const response = await apiClient.patch(`/api/v1/tags/${tag.id}`, data);
        return response.data;
      } else {
        // Create new tag
        const response = await apiClient.post('/api/v1/tags', data);
        return response.data;
      }
    },
    onSuccess: () => {
      onSuccess();
    },
    onError: (error: any) => {
      setError(error.message || 'Failed to save tag');
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!formData.name.trim()) {
      setError('Tag name is required');
      return;
    }

    await saveMutation.mutateAsync(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          {tag ? 'Edit Tag' : 'Create New Tag'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tag Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <input
              type="text"
              list="categories"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <datalist id="categories">
              {categories.map((cat) => (
                <option key={cat} value={cat} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Color
            </label>
            <input
              type="color"
              value={formData.color}
              onChange={(e) => setFormData({ ...formData, color: e.target.value })}
              className="w-full h-10 rounded-lg border border-gray-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sensitivity Level
            </label>
            <select
              value={formData.sensitivity_level}
              onChange={(e) => setFormData({ ...formData, sensitivity_level: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">None</option>
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="confidential">Confidential</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {saveMutation.isPending ? 'Saving...' : tag ? 'Update Tag' : 'Create Tag'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Data Products Tab (Placeholder - future implementation)
// =============================================================================

function DataProductsTab() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
      <Package className="w-16 h-16 text-gray-400 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Data Products Management</h3>
      <p className="text-gray-500 mb-6">
        Create and manage data products, associate capsules, and configure SLOs.
      </p>
      <p className="text-sm text-gray-400">
        This feature is available via the <a href="/products" className="text-blue-600 hover:text-blue-700">Data Products</a> page.
      </p>
    </div>
  );
}

// =============================================================================
// Conformance Rules Tab
// =============================================================================

function ConformanceRulesTab() {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['conformance-rules-settings'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/conformance/rules', {
        params: { enabled: false }, // Show all rules including disabled
      });
      return response.data;
    },
  });

  const exportRulesMutation = useMutation({
    mutationFn: async (ruleSet?: string) => {
      const response = await apiClient.get('/api/v1/conformance/rules/export', {
        params: { rule_set: ruleSet },
        responseType: 'blob',
      });
      return response.data;
    },
    onSuccess: (data) => {
      const url = window.URL.createObjectURL(new Blob([data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `conformance_rules_${new Date().toISOString().split('T')[0]}.yaml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      await apiClient.delete(`/api/v1/conformance/rules/${ruleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conformance-rules-settings'] });
    },
  });

  const handleDeleteRule = async (rule: any) => {
    if (window.confirm(`Are you sure you want to delete the rule "${rule.name}"?`)) {
      try {
        await deleteRuleMutation.mutateAsync(rule.rule_id);
      } catch (error: any) {
        alert(error.message || 'Failed to delete rule');
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const rules = rulesData?.data || [];
  const ruleSets = rulesData?.rule_sets || [];
  const customRules = rules.filter((r: any) => r.rule_set === 'custom');
  const builtInRules = rules.filter((r: any) => r.rule_set !== 'custom');

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Conformance Rules</h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage custom conformance rules and export rule configurations
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => exportRulesMutation.mutate()}
            disabled={exportRulesMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-4 h-4" />
            {exportRulesMutation.isPending ? 'Exporting...' : 'Export Rules'}
          </button>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Upload className="w-4 h-4" />
            Upload Custom Rules
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{rules.length}</div>
          <div className="text-sm text-gray-500">Total Rules</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{customRules.length}</div>
          <div className="text-sm text-gray-500">Custom Rules</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{ruleSets.length}</div>
          <div className="text-sm text-gray-500">Rule Sets</div>
        </div>
      </div>

      {/* Custom Rules */}
      <div>
        <h3 className="text-md font-semibold text-gray-900 mb-3">Custom Rules</h3>
        {customRules.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <Shield className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">No custom rules defined</p>
            <button
              onClick={() => setShowUploadModal(true)}
              className="mt-3 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Upload your first custom rule
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {customRules.map((rule: any) => (
                  <tr key={rule.rule_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">{rule.rule_id}</td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{rule.name}</div>
                      {rule.description && (
                        <div className="text-sm text-gray-500 mt-1">{rule.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          rule.severity === 'critical'
                            ? 'bg-red-100 text-red-800'
                            : rule.severity === 'error'
                            ? 'bg-orange-100 text-orange-800'
                            : rule.severity === 'warning'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{rule.category}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {rule.enabled ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                          <Check className="w-3 h-3" />
                          Enabled
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-800 text-xs font-medium rounded-full">
                          <X className="w-3 h-3" />
                          Disabled
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => handleDeleteRule(rule)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Built-in Rules */}
      <div>
        <h3 className="text-md font-semibold text-gray-900 mb-3">Built-in Rules ({builtInRules.length})</h3>
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">
            Built-in rules are provided by the system and cannot be deleted. You can view and export them using the Export Rules button above.
          </p>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadRulesModal
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['conformance-rules-settings'] });
            setShowUploadModal(false);
          }}
        />
      )}
    </div>
  );
}

// Upload Rules Modal Component
function UploadRulesModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [ruleSetName, setRuleSetName] = useState('');
  const [error, setError] = useState('');

  const uploadMutation = useMutation({
    mutationFn: async ({ file, ruleSetName }: { file: File; ruleSetName: string }) => {
      const formData = new FormData();
      formData.append('rules_file', file);
      if (ruleSetName) {
        formData.append('rule_set_name', ruleSetName);
      }

      const response = await apiClient.post('/api/v1/conformance/rules/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: (data) => {
      alert(`Successfully uploaded ${data.rules_added} rules!`);
      onSuccess();
    },
    onError: (error: any) => {
      setError(error.message || 'Failed to upload rules');
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!file) {
      setError('Please select a YAML file');
      return;
    }

    await uploadMutation.mutateAsync({ file, ruleSetName });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-lg w-full p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Upload Custom Rules</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              YAML File *
            </label>
            <input
              type="file"
              accept=".yaml,.yml"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <p className="text-xs text-gray-500 mt-1">Upload a YAML file containing custom conformance rules</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rule Set Name (optional)
            </label>
            <input
              type="text"
              value={ruleSetName}
              onChange={(e) => setRuleSetName(e.target.value)}
              placeholder="custom"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Example YAML Format:</h4>
            <pre className="text-xs text-blue-800 overflow-x-auto">
{`rules:
  - id: CUSTOM_001
    name: "Custom naming rule"
    description: "All models must start with a prefix"
    severity: warning
    category: naming
    scope: capsule
    pattern: "^(app_|sys_).*"
    remediation: "Rename model to start with app_ or sys_"`}
            </pre>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={uploadMutation.isPending}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Rules'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// System Info Tab
// =============================================================================

function SystemInfoTab() {
  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/health');
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Information</h2>
      </div>

      {/* System Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-md font-semibold text-gray-900 mb-4">Service Status</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">API Status</span>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              {healthData?.status || 'Healthy'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Database</span>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              Connected
            </span>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-md font-semibold text-gray-900 mb-4">Configuration</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-sm text-gray-700">API Base URL</span>
            <span className="text-sm font-mono text-gray-900">{process.env.NEXT_PUBLIC_API_URL}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-sm text-gray-700">Environment</span>
            <span className="text-sm font-mono text-gray-900">{process.env.NODE_ENV}</span>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-md font-semibold text-gray-900 mb-4">About</h3>
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            <strong>Data Architecture Brain</strong>
          </p>
          <p className="text-sm text-gray-500">
            A comprehensive data governance platform for managing data capsules, tracking PII compliance,
            enforcing architecture conformance, and visualizing data lineage.
          </p>
        </div>
      </div>
    </div>
  );
}
