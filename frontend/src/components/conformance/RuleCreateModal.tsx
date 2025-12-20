'use client';

/**
 * Rule Create/Edit Modal Component
 *
 * Form for creating or editing custom conformance rules with validation.
 */

import { useState } from 'react';
import { X, Plus, AlertCircle } from 'lucide-react';
import Badge from '@/components/common/Badge';

interface RuleFormData {
  rule_id: string;
  name: string;
  description: string;
  severity: 'critical' | 'error' | 'warning' | 'info';
  category: string;
  scope: 'capsule' | 'column' | 'domain' | 'global';
  pattern: string;
  remediation: string;
}

interface RuleCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (rule: RuleFormData) => Promise<void>;
  initialData?: Partial<RuleFormData>;
  mode?: 'create' | 'edit';
}

const CATEGORIES = [
  'naming',
  'documentation',
  'pii_compliance',
  'structural',
  'semantic',
  'quality',
  'policy',
  'provenance',
  'operational',
];

export default function RuleCreateModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode = 'create',
}: RuleCreateModalProps) {
  const [formData, setFormData] = useState<RuleFormData>({
    rule_id: initialData?.rule_id || '',
    name: initialData?.name || '',
    description: initialData?.description || '',
    severity: initialData?.severity || 'warning',
    category: initialData?.category || 'naming',
    scope: initialData?.scope || 'capsule',
    pattern: initialData?.pattern || '',
    remediation: initialData?.remediation || '',
  });

  const [errors, setErrors] = useState<Partial<Record<keyof RuleFormData, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof RuleFormData, string>> = {};

    // Rule ID validation
    if (!formData.rule_id.trim()) {
      newErrors.rule_id = 'Rule ID is required';
    } else if (!/^[A-Z_0-9]+$/.test(formData.rule_id)) {
      newErrors.rule_id = 'Rule ID must contain only uppercase letters, numbers, and underscores';
    }

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (formData.name.length < 5) {
      newErrors.name = 'Name must be at least 5 characters';
    }

    // Description validation
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    }

    // Pattern validation (optional but if provided, must be valid regex)
    if (formData.pattern.trim()) {
      try {
        new RegExp(formData.pattern);
      } catch (e) {
        newErrors.pattern = 'Invalid regular expression pattern';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error('Failed to submit rule:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    field: keyof RuleFormData,
    value: string
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {mode === 'create' ? 'Create Custom Rule' : 'Edit Rule'}
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {mode === 'create'
                    ? 'Define a new custom conformance rule for your data architecture'
                    : 'Update the configuration of this custom rule'}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Rule ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule ID *
              </label>
              <input
                type="text"
                value={formData.rule_id}
                onChange={(e) => handleChange('rule_id', e.target.value.toUpperCase())}
                placeholder="CUSTOM_001"
                disabled={mode === 'edit'}
                className={`w-full px-4 py-2 border rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.rule_id ? 'border-red-500' : 'border-gray-300'
                } ${mode === 'edit' ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              />
              {errors.rule_id && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.rule_id}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Unique identifier using uppercase letters, numbers, and underscores
              </p>
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="e.g., Tables must have primary keys"
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.name ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.name}
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description *
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Explain what this rule checks for and why it's important..."
                rows={4}
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.description ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.description}
                </p>
              )}
            </div>

            {/* Grid for Severity, Category, Scope */}
            <div className="grid grid-cols-3 gap-4">
              {/* Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Severity *
                </label>
                <select
                  value={formData.severity}
                  onChange={(e) =>
                    handleChange('severity', e.target.value as RuleFormData['severity'])
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="critical">Critical</option>
                  <option value="error">Error</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category *
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => handleChange('category', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {formatCategory(cat)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Scope */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scope *
                </label>
                <select
                  value={formData.scope}
                  onChange={(e) =>
                    handleChange('scope', e.target.value as RuleFormData['scope'])
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="capsule">Capsule</option>
                  <option value="column">Column</option>
                  <option value="domain">Domain</option>
                  <option value="global">Global</option>
                </select>
              </div>
            </div>

            {/* Pattern */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pattern (Optional)
              </label>
              <input
                type="text"
                value={formData.pattern}
                onChange={(e) => handleChange('pattern', e.target.value)}
                placeholder="^(stg_|dim_|fct_).*"
                className={`w-full px-4 py-2 border rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.pattern ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {errors.pattern && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.pattern}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Regular expression pattern for name-based validation
              </p>
            </div>

            {/* Remediation */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Remediation (Optional)
              </label>
              <textarea
                value={formData.remediation}
                onChange={(e) => handleChange('remediation', e.target.value)}
                placeholder="Provide step-by-step instructions on how to fix violations of this rule..."
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="mt-1 text-xs text-gray-500">
                Recommended actions for resolving violations
              </p>
            </div>

            {/* Preview */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-900 mb-2">Preview</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant={getSeverityVariant(formData.severity)} size="sm">
                    {formData.severity}
                  </Badge>
                  <Badge variant="default" size="sm">
                    {formatCategory(formData.category)}
                  </Badge>
                  <Badge variant="info" size="sm">
                    Custom
                  </Badge>
                </div>
                <p className="text-sm text-gray-900 font-medium">
                  {formData.name || 'Rule name...'}
                </p>
                <p className="text-xs text-gray-600">
                  {formData.description || 'Rule description...'}
                </p>
              </div>
            </div>
          </form>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-6 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {mode === 'create' ? 'Creating...' : 'Updating...'}
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  {mode === 'create' ? 'Create Rule' : 'Update Rule'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Functions

function getSeverityVariant(
  severity: string
): 'danger' | 'warning' | 'info' | 'default' {
  switch (severity) {
    case 'critical':
      return 'danger';
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'default';
  }
}

function formatCategory(category: string): string {
  return category
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
