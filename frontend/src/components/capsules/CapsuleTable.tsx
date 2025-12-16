'use client';

/**
 * Capsule Table Component
 *
 * Table display for data capsules with badges and navigation.
 */

import { useRouter } from 'next/navigation';
import { Database, FileText, Package, Camera, BarChart } from 'lucide-react';
import { CapsuleSummary, CapsuleType } from '@/lib/api/types';
import Badge from '@/components/common/Badge';
import { clsx } from 'clsx';

interface CapsuleTableProps {
  capsules: CapsuleSummary[];
  className?: string;
}

// Icon mapping for capsule types
const typeIcons: Record<CapsuleType, React.ReactNode> = {
  model: <Database className="w-4 h-4" />,
  source: <FileText className="w-4 h-4" />,
  seed: <Package className="w-4 h-4" />,
  snapshot: <Camera className="w-4 h-4" />,
  analysis: <BarChart className="w-4 h-4" />,
};

export default function CapsuleTable({ capsules, className }: CapsuleTableProps) {
  const router = useRouter();

  const handleRowClick = (urn: string) => {
    router.push(`/capsules/${encodeURIComponent(urn)}`);
  };

  if (capsules.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No capsules found</h3>
        <p className="text-gray-600">
          Try adjusting your filters or search query to find more capsules.
        </p>
      </div>
    );
  }

  return (
    <div className={clsx('bg-white rounded-lg shadow overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Layer
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Domain
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Columns
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                PII
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {capsules.map((capsule) => (
              <tr
                key={capsule.id}
                onClick={() => handleRowClick(capsule.urn)}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
              >
                {/* Name */}
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 p-2 bg-blue-50 text-blue-600 rounded-lg">
                      {typeIcons[capsule.type]}
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-gray-900 truncate">{capsule.name}</div>
                      {capsule.description && (
                        <div className="text-sm text-gray-500 truncate max-w-md">
                          {capsule.description}
                        </div>
                      )}
                    </div>
                  </div>
                </td>

                {/* Type */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <Badge variant="default" size="sm">
                    {capsule.type}
                  </Badge>
                </td>

                {/* Layer */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {capsule.layer ? (
                    <Badge variant={capsule.layer as any} size="sm">
                      {capsule.layer}
                    </Badge>
                  ) : (
                    <span className="text-sm text-gray-400">-</span>
                  )}
                </td>

                {/* Domain */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {capsule.domain_name ? (
                    <span className="text-sm text-gray-900">{capsule.domain_name}</span>
                  ) : (
                    <span className="text-sm text-gray-400">-</span>
                  )}
                </td>

                {/* Columns */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900">{capsule.column_count}</span>
                </td>

                {/* PII */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {capsule.has_pii ? (
                    <Badge variant="pii" size="sm">
                      {capsule.pii_column_count} PII
                    </Badge>
                  ) : (
                    <Badge variant="no-pii" size="sm">
                      None
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
