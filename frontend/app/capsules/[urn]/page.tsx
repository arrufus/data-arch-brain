'use client';

/**
 * Capsule Detail Page
 *
 * Detailed view of a single data capsule with tabs for columns, lineage, and violations.
 */

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useCapsuleDetail } from '@/lib/api/capsules';
import { ArrowLeft, Database, FileText, Package, Camera, BarChart, ExternalLink } from 'lucide-react';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import Badge from '@/components/common/Badge';
import ColumnsTab from '@/components/capsules/ColumnsTab';
import LineageTab from '@/components/capsules/LineageTab';
import ViolationsTab from '@/components/capsules/ViolationsTab';

type TabType = 'columns' | 'lineage' | 'violations';

// Icon mapping for capsule types
const typeIcons = {
  model: Database,
  source: FileText,
  seed: Package,
  snapshot: Camera,
  analysis: BarChart,
};

export default function CapsuleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const urn = decodeURIComponent(params.urn as string);

  const [activeTab, setActiveTab] = useState<TabType>('columns');

  // Fetch capsule detail
  const { data: capsule, isLoading, error, refetch } = useCapsuleDetail(urn);

  if (isLoading) {
    return (
      <div className="py-12">
        <Loading size="lg" text="Loading capsule details..." />
      </div>
    );
  }

  if (error || !capsule) {
    return (
      <ErrorMessage
        title="Failed to load capsule"
        message={error?.message || 'Capsule not found'}
        onRetry={refetch}
      />
    );
  }

  const TypeIcon = typeIcons[capsule.type as keyof typeof typeIcons] || Database;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push('/capsules')}
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Capsules
      </button>

      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg flex-shrink-0">
            <TypeIcon className="w-8 h-8" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-gray-900 truncate">{capsule.name}</h1>
              <Badge variant={capsule.type as any}>{capsule.type}</Badge>
              {capsule.layer && <Badge variant={capsule.layer as any}>{capsule.layer}</Badge>}
            </div>
            {capsule.description && (
              <p className="text-gray-600 mb-4">{capsule.description}</p>
            )}
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <span className="font-mono">{urn}</span>
              <a
                href={`http://localhost:8002/api/v1/docs#/capsules/get_capsule_api_v1_capsules__urn__detail_get`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
              >
                <ExternalLink className="w-3 h-3" />
                API
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetadataCard label="Owner" value={capsule.owner || 'Unknown'} />
        <MetadataCard label="Domain" value={capsule.domain_name || 'None'} />
        <MetadataCard label="Columns" value={capsule.column_count} />
        <MetadataCard
          label="PII Columns"
          value={capsule.pii_column_count}
          badge={capsule.has_pii ? 'pii' : 'no-pii'}
        />
        <MetadataCard label="Database" value={capsule.database_name || '-'} />
        <MetadataCard label="Schema" value={capsule.schema_name || '-'} />
        <MetadataCard label="Upstream" value={capsule.upstream_count} />
        <MetadataCard label="Downstream" value={capsule.downstream_count} />
      </div>

      {/* Additional Info */}
      {(capsule.source_system || capsule.materialization || capsule.tags?.length > 0) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Additional Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {capsule.source_system && (
              <div>
                <span className="text-sm text-gray-600">Source System:</span>
                <p className="font-medium text-gray-900">{capsule.source_system}</p>
              </div>
            )}
            {capsule.materialization && (
              <div>
                <span className="text-sm text-gray-600">Materialization:</span>
                <p className="font-medium text-gray-900">{capsule.materialization}</p>
              </div>
            )}
            {capsule.tags && capsule.tags.length > 0 && (
              <div className="md:col-span-2">
                <span className="text-sm text-gray-600 block mb-2">Tags:</span>
                <div className="flex flex-wrap gap-2">
                  {capsule.tags.map((tag) => (
                    <Badge key={tag} variant="default">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-8 px-6" aria-label="Tabs">
            <TabButton
              active={activeTab === 'columns'}
              onClick={() => setActiveTab('columns')}
              badge={capsule.column_count}
            >
              Columns
            </TabButton>
            <TabButton
              active={activeTab === 'lineage'}
              onClick={() => setActiveTab('lineage')}
              badge={capsule.upstream_count + capsule.downstream_count}
            >
              Lineage
            </TabButton>
            <TabButton
              active={activeTab === 'violations'}
              onClick={() => setActiveTab('violations')}
            >
              Violations
            </TabButton>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'columns' && <ColumnsTab capsuleUrn={urn} />}
          {activeTab === 'lineage' && <LineageTab capsuleUrn={urn} />}
          {activeTab === 'violations' && <ViolationsTab capsuleUrn={urn} />}
        </div>
      </div>
    </div>
  );
}

// Metadata Card Component
function MetadataCard({
  label,
  value,
  badge,
}: {
  label: string;
  value: string | number;
  badge?: 'pii' | 'no-pii';
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-sm text-gray-600 mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <p className="text-lg font-semibold text-gray-900">{value}</p>
        {badge && (
          <Badge variant={badge} size="sm">
            {badge === 'pii' ? 'PII' : 'None'}
          </Badge>
        )}
      </div>
    </div>
  );
}

// Tab Button Component
function TabButton({
  active,
  onClick,
  children,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        py-4 border-b-2 font-medium text-sm transition-colors
        ${
          active
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }
      `}
    >
      <span className="flex items-center gap-2">
        {children}
        {badge !== undefined && (
          <span
            className={`
              px-2 py-0.5 rounded-full text-xs font-medium
              ${active ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}
            `}
          >
            {badge}
          </span>
        )}
      </span>
    </button>
  );
}
