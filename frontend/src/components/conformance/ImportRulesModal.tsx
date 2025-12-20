'use client';

/**
 * Import Rules Modal Component
 *
 * Upload and preview YAML file containing custom conformance rules.
 */

import { useState, useRef } from 'react';
import { X, Upload, FileText, AlertCircle, CheckCircle, Download } from 'lucide-react';
import Badge from '@/components/common/Badge';

interface ParsedRule {
  id: string;
  name: string;
  description: string;
  severity: string;
  category: string;
  scope: string;
  pattern?: string;
  remediation?: string;
}

interface ImportRulesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (yamlContent: string, ruleSetName?: string) => Promise<{ rules_added: number; rule_ids: string[] }>;
}

export default function ImportRulesModal({
  isOpen,
  onClose,
  onImport,
}: ImportRulesModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [yamlContent, setYamlContent] = useState<string>('');
  const [parsedRules, setParsedRules] = useState<ParsedRule[]>([]);
  const [ruleSetName, setRuleSetName] = useState<string>('');
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Check file type
    if (!selectedFile.name.endsWith('.yaml') && !selectedFile.name.endsWith('.yml')) {
      setError('Please select a YAML file (.yaml or .yml)');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setIsValidating(true);

    try {
      const content = await selectedFile.text();
      setYamlContent(content);

      // Basic YAML validation (check if it has rules key)
      const rules = parseYAMLRules(content);
      if (rules.length === 0) {
        throw new Error('No rules found in YAML file. Please ensure the file contains a "rules" key with rule definitions.');
      }

      setParsedRules(rules);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse YAML file');
      setParsedRules([]);
    } finally {
      setIsValidating(false);
    }
  };

  const parseYAMLRules = (content: string): ParsedRule[] => {
    // Simple YAML parsing for rules
    // In production, use a proper YAML parser like js-yaml
    const rules: ParsedRule[] = [];

    try {
      // Basic validation - check for rules: keyword
      if (!content.includes('rules:')) {
        return [];
      }

      // Extract rule blocks (simplified parsing)
      const ruleBlocks = content.split(/- id:/g).slice(1);

      ruleBlocks.forEach((block, index) => {
        const id = extractValue(block, 'id') || `RULE_${index + 1}`;
        const name = extractValue(block, 'name') || 'Unnamed Rule';
        const description = extractValue(block, 'description') || '';
        const severity = extractValue(block, 'severity') || 'warning';
        const category = extractValue(block, 'category') || 'naming';
        const scope = extractValue(block, 'scope') || 'capsule';
        const pattern = extractValue(block, 'pattern');
        const remediation = extractValue(block, 'remediation');

        rules.push({
          id,
          name,
          description,
          severity,
          category,
          scope,
          pattern,
          remediation,
        });
      });
    } catch (err) {
      console.error('Error parsing YAML:', err);
    }

    return rules;
  };

  const extractValue = (block: string, key: string): string | undefined => {
    const regex = new RegExp(`${key}:\\s*["']?([^"'\\n]+)["']?`);
    const match = block.match(regex);
    return match ? match[1].trim() : undefined;
  };

  const handleImport = async () => {
    if (!yamlContent || parsedRules.length === 0) {
      setError('Please select a valid YAML file first');
      return;
    }

    setIsImporting(true);
    setError(null);

    try {
      await onImport(yamlContent, ruleSetName || undefined);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import rules');
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setYamlContent('');
    setParsedRules([]);
    setRuleSetName('');
    setError(null);
    onClose();
  };

  const downloadExampleYAML = () => {
    const exampleYAML = `rules:
  - id: CUSTOM_001
    name: "Custom naming rule"
    description: "All models must start with a prefix"
    severity: warning
    category: naming
    scope: capsule
    pattern: "^(app_|sys_).*"
    remediation: "Rename model to start with app_ or sys_"

  - id: CUSTOM_002
    name: "Tables must have descriptions"
    description: "All tables should have documentation"
    severity: error
    category: documentation
    scope: capsule
    remediation: "Add a description to the table in dbt or documentation"`

;

    const blob = new Blob([exampleYAML], { type: 'application/x-yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'example_rules.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Import Rules from YAML</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Upload a YAML file containing custom conformance rules
                </p>
              </div>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Example Template */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900">
                      Need an example template?
                    </p>
                    <p className="text-sm text-blue-700 mt-1">
                      Download a sample YAML file to see the expected format
                    </p>
                  </div>
                </div>
                <button
                  onClick={downloadExampleYAML}
                  className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download Example
                </button>
              </div>
            </div>

            {/* Rule Set Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule Set Name (Optional)
              </label>
              <input
                type="text"
                value={ruleSetName}
                onChange={(e) => setRuleSetName(e.target.value)}
                placeholder="e.g., custom_company_rules"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="mt-1 text-xs text-gray-500">
                Optional identifier for grouping these rules together
              </p>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                YAML File
              </label>
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  file
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".yaml,.yml"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Upload className={`w-12 h-12 mx-auto mb-4 ${file ? 'text-green-600' : 'text-gray-400'}`} />
                {file ? (
                  <div>
                    <p className="text-lg font-medium text-green-900 mb-1">{file.name}</p>
                    <p className="text-sm text-green-700">
                      {parsedRules.length} rule{parsedRules.length !== 1 ? 's' : ''} found
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-lg font-medium text-gray-900 mb-1">
                      Click to upload YAML file
                    </p>
                    <p className="text-sm text-gray-600">
                      or drag and drop your file here
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-900">Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Validating */}
            {isValidating && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-blue-900">Validating YAML file...</p>
              </div>
            )}

            {/* Preview Rules */}
            {parsedRules.length > 0 && !error && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  Preview ({parsedRules.length} rules)
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {parsedRules.map((rule, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={getSeverityVariant(rule.severity)} size="sm">
                            {rule.severity}
                          </Badge>
                          <Badge variant="default" size="sm">
                            {formatCategory(rule.category)}
                          </Badge>
                        </div>
                        <code className="text-xs font-mono text-gray-600">{rule.id}</code>
                      </div>
                      <h4 className="font-medium text-gray-900 mb-1">{rule.name}</h4>
                      <p className="text-sm text-gray-600">{rule.description}</p>
                      {rule.pattern && (
                        <div className="mt-2">
                          <code className="text-xs bg-white px-2 py-1 rounded border border-gray-200 font-mono">
                            {rule.pattern}
                          </code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isImporting}
              className="px-6 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleImport}
              disabled={isImporting || parsedRules.length === 0 || !!error}
              className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isImporting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Import {parsedRules.length} Rule{parsedRules.length !== 1 ? 's' : ''}
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
  switch (severity.toLowerCase()) {
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
