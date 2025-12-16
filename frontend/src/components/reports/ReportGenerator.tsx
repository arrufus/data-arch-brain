'use client';

/**
 * Report Generator Component
 *
 * Handles report configuration, generation, and download.
 */

import { useState } from 'react';
import { Download, Filter, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import {
  downloadPIIInventoryReport,
  downloadConformanceReport,
  downloadCapsuleSummaryReport,
  triggerDownload,
  generateFilename,
  type ReportFormat,
  type ReportFilters,
} from '@/lib/api/reports';

interface ReportGeneratorProps {
  reportType: 'pii-inventory' | 'conformance' | 'capsule-summary';
}

export default function ReportGenerator({ reportType }: ReportGeneratorProps) {
  const [format, setFormat] = useState<ReportFormat>('json');
  const [filters, setFilters] = useState<ReportFilters>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setToast(null);

    try {
      let blob: Blob;
      let filename: string;

      switch (reportType) {
        case 'pii-inventory':
          blob = await downloadPIIInventoryReport(format, filters);
          filename = generateFilename('pii_inventory', format);
          break;
        case 'conformance':
          blob = await downloadConformanceReport(format, filters);
          filename = generateFilename('conformance', format);
          break;
        case 'capsule-summary':
          // Capsule summary only supports JSON and CSV
          const capsuleFormat = format === 'html' ? 'json' : format;
          blob = await downloadCapsuleSummaryReport(capsuleFormat, filters);
          filename = generateFilename('capsule_summary', capsuleFormat);
          break;
      }

      triggerDownload(blob, filename);
      setToast({ type: 'success', message: `Report downloaded successfully: ${filename}` });
    } catch (error: any) {
      console.error('Report generation error:', error);
      setToast({
        type: 'error',
        message: error?.response?.data?.detail || error.message || 'Failed to generate report',
      });
    } finally {
      setIsGenerating(false);
      // Auto-hide toast after 5 seconds
      setTimeout(() => setToast(null), 5000);
    }
  };

  const updateFilter = (key: keyof ReportFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === 'all' ? undefined : value,
    }));
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      {/* Format Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Output Format</label>
        <div className="flex gap-3">
          <FormatButton
            format="json"
            label="JSON"
            description="Structured data"
            active={format === 'json'}
            onClick={() => setFormat('json')}
          />
          <FormatButton
            format="csv"
            label="CSV"
            description="Spreadsheet compatible"
            active={format === 'csv'}
            onClick={() => setFormat('csv')}
          />
          {reportType !== 'capsule-summary' && (
            <FormatButton
              format="html"
              label="HTML"
              description="Formatted report"
              active={format === 'html'}
              onClick={() => setFormat('html')}
            />
          )}
        </div>
      </div>

      {/* Filters */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-gray-600" />
          <label className="text-sm font-medium text-gray-700">Filters (Optional)</label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* PII Inventory Filters */}
          {reportType === 'pii-inventory' && (
            <>
              <FilterSelect
                label="Layer"
                value={filters.layer || 'all'}
                onChange={(value) => updateFilter('layer', value)}
                options={[
                  { value: 'all', label: 'All Layers' },
                  { value: 'raw', label: 'Raw' },
                  { value: 'bronze', label: 'Bronze' },
                  { value: 'silver', label: 'Silver' },
                  { value: 'gold', label: 'Gold' },
                  { value: 'marts', label: 'Marts' },
                ]}
              />
              <FilterSelect
                label="PII Type"
                value={filters.piiType || 'all'}
                onChange={(value) => updateFilter('piiType', value)}
                options={[
                  { value: 'all', label: 'All Types' },
                  { value: 'name', label: 'Name' },
                  { value: 'email', label: 'Email' },
                  { value: 'phone', label: 'Phone' },
                  { value: 'address', label: 'Address' },
                  { value: 'ssn', label: 'SSN' },
                  { value: 'credit_card', label: 'Credit Card' },
                ]}
              />
            </>
          )}

          {/* Conformance Filters */}
          {reportType === 'conformance' && (
            <>
              <FilterSelect
                label="Severity"
                value={filters.severity || 'all'}
                onChange={(value) => updateFilter('severity', value)}
                options={[
                  { value: 'all', label: 'All Severities' },
                  { value: 'critical', label: 'Critical' },
                  { value: 'error', label: 'Error' },
                  { value: 'warning', label: 'Warning' },
                  { value: 'info', label: 'Info' },
                ]}
              />
              <FilterSelect
                label="Rule Set"
                value={filters.ruleSet || 'all'}
                onChange={(value) => updateFilter('ruleSet', value)}
                options={[
                  { value: 'all', label: 'All Rule Sets' },
                  { value: 'naming', label: 'Naming' },
                  { value: 'layering', label: 'Layering' },
                  { value: 'documentation', label: 'Documentation' },
                  { value: 'testing', label: 'Testing' },
                ]}
              />
            </>
          )}

          {/* Capsule Summary Filters */}
          {reportType === 'capsule-summary' && (
            <>
              <FilterSelect
                label="Layer"
                value={filters.layer || 'all'}
                onChange={(value) => updateFilter('layer', value)}
                options={[
                  { value: 'all', label: 'All Layers' },
                  { value: 'raw', label: 'Raw' },
                  { value: 'bronze', label: 'Bronze' },
                  { value: 'silver', label: 'Silver' },
                  { value: 'gold', label: 'Gold' },
                  { value: 'marts', label: 'Marts' },
                ]}
              />
              <FilterSelect
                label="Capsule Type"
                value={filters.capsuleType || 'all'}
                onChange={(value) => updateFilter('capsuleType', value)}
                options={[
                  { value: 'all', label: 'All Types' },
                  { value: 'model', label: 'Model' },
                  { value: 'source', label: 'Source' },
                  { value: 'seed', label: 'Seed' },
                  { value: 'snapshot', label: 'Snapshot' },
                  { value: 'analysis', label: 'Analysis' },
                ]}
              />
            </>
          )}
        </div>
      </div>

      {/* Generate Button */}
      <div className="flex items-center gap-4 pt-4 border-t">
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Loader className="w-5 h-5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              Generate & Download
            </>
          )}
        </button>

        {/* Info text */}
        <p className="text-sm text-gray-600">
          Report will be downloaded as <span className="font-mono">{generateFilename(reportType, format)}</span>
        </p>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div
          className={`flex items-center gap-3 p-4 rounded-lg ${
            toast.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          )}
          <p className={`text-sm ${toast.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
            {toast.message}
          </p>
          <button
            onClick={() => setToast(null)}
            className={`ml-auto text-sm font-medium ${
              toast.type === 'success' ? 'text-green-600 hover:text-green-800' : 'text-red-600 hover:text-red-800'
            }`}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}

// Format Button Component
function FormatButton({
  format,
  label,
  description,
  active,
  onClick,
}: {
  format: string;
  label: string;
  description: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex-1 p-4 border-2 rounded-lg transition-all text-left
        ${active ? 'border-blue-600 bg-blue-50' : 'border-gray-200 bg-white hover:border-blue-300'}
      `}
    >
      <div className="font-medium text-gray-900">{label}</div>
      <div className="text-xs text-gray-600 mt-1">{description}</div>
    </button>
  );
}

// Filter Select Component
function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
