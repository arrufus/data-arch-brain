'use client';

/**
 * Reports Page
 *
 * Generate and download reports in various formats.
 */

import { useState } from 'react';
import { FileText, Download, Filter, CheckCircle } from 'lucide-react';
import ReportGenerator from '@/components/reports/ReportGenerator';

type ReportType = 'pii-inventory' | 'conformance' | 'capsule-summary';

export default function ReportsPage() {
  const [selectedReport, setSelectedReport] = useState<ReportType>('pii-inventory');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports & Export</h1>
        <p className="mt-2 text-gray-600">
          Generate and download comprehensive reports in JSON, CSV, or HTML format
        </p>
      </div>

      {/* Report Type Selection */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Select Report Type</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ReportTypeCard
            title="PII Inventory"
            description="Comprehensive list of all PII columns detected across your data architecture"
            icon={<FileText className="w-6 h-6" />}
            active={selectedReport === 'pii-inventory'}
            onClick={() => setSelectedReport('pii-inventory')}
            features={[
              'PII types distribution',
              'Layer-based breakdown',
              'Detailed column information',
              'Detection methods',
            ]}
          />
          <ReportTypeCard
            title="Conformance Report"
            description="Architecture conformance scores, rule evaluations, and violations"
            icon={<CheckCircle className="w-6 h-6" />}
            active={selectedReport === 'conformance'}
            onClick={() => setSelectedReport('conformance')}
            features={[
              'Overall conformance score',
              'Category-wise breakdown',
              'Violation details',
              'Severity indicators',
            ]}
          />
          <ReportTypeCard
            title="Capsule Summary"
            description="Complete inventory of all data capsules with metadata and statistics"
            icon={<Download className="w-6 h-6" />}
            active={selectedReport === 'capsule-summary'}
            onClick={() => setSelectedReport('capsule-summary')}
            features={[
              'Capsule metadata',
              'Column counts',
              'PII indicators',
              'Test coverage',
            ]}
          />
        </div>
      </div>

      {/* Report Generator */}
      <ReportGenerator reportType={selectedReport} />
    </div>
  );
}

// Report Type Card Component
function ReportTypeCard({
  title,
  description,
  icon,
  active,
  onClick,
  features,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
  features: string[];
}) {
  return (
    <button
      onClick={onClick}
      className={`
        text-left p-6 border-2 rounded-lg transition-all
        ${
          active
            ? 'border-blue-600 bg-blue-50 shadow-md'
            : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50'
        }
      `}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg ${active ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-600'}`}>
          {icon}
        </div>
        <h3 className="font-semibold text-gray-900">{title}</h3>
      </div>
      <p className="text-sm text-gray-600 mb-4">{description}</p>
      <ul className="space-y-1">
        {features.map((feature, index) => (
          <li key={index} className="text-xs text-gray-500 flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-blue-600' : 'bg-gray-400'}`} />
            {feature}
          </li>
        ))}
      </ul>
    </button>
  );
}
