'use client';

/**
 * Column Detail Panel Component (Phase 7)
 *
 * Side panel displaying comprehensive metadata for a selected column
 */

import { useColumnTransformations, useUpstreamColumns, useDownstreamColumns } from '@/lib/api/column-lineage';
import {
  X,
  Database,
  Table2,
  ArrowRight,
  ArrowLeft,
  Code2,
  Info,
  Tag,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
} from 'lucide-react';

interface ColumnDetailPanelProps {
  columnUrn: string;
  onClose: () => void;
  onNavigate?: (columnUrn: string) => void;
}

export default function ColumnDetailPanel({
  columnUrn,
  onClose,
  onNavigate,
}: ColumnDetailPanelProps) {
  const { data: transformations, isLoading: transformationsLoading } =
    useColumnTransformations(columnUrn);
  const { data: upstreamData, isLoading: upstreamLoading } = useUpstreamColumns(columnUrn, {
    depth: 1,
    limit: 10,
  });
  const { data: downstreamData, isLoading: downstreamLoading } = useDownstreamColumns(columnUrn, {
    depth: 1,
    limit: 10,
  });

  // Extract column name from URN
  const columnParts = columnUrn.split(':');
  const columnName = columnParts[columnParts.length - 1] || 'Unknown';
  const capsuleName = columnParts[columnParts.length - 2] || '';

  const upstreamColumns = upstreamData?.upstream_columns || [];
  const downstreamColumns = downstreamData?.downstream_columns || [];
  const transformationList = transformations?.transformations || [];

  return (
    <div className="fixed right-0 top-0 h-full w-[500px] bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Table2 className="w-5 h-5 text-gray-600 flex-shrink-0" />
            <h2 className="text-lg font-semibold text-gray-900 truncate">{columnName}</h2>
          </div>
          <p className="text-sm text-gray-600 font-mono truncate">{columnUrn}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors flex-shrink-0"
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Basic Info */}
          <Section title="Basic Info" icon={<Info className="w-4 h-4" />}>
            <DataList>
              <DataItem label="Column Name" value={columnName} />
              <DataItem label="Capsule" value={capsuleName} />
              <DataItem label="URN" value={columnUrn} mono />
            </DataList>
          </Section>

          {/* Lineage Summary */}
          <Section title="Lineage Summary" icon={<ArrowRight className="w-4 h-4" />}>
            <div className="grid grid-cols-2 gap-4">
              {/* Upstream Card */}
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <ArrowLeft className="w-4 h-4 text-blue-600" />
                  <div className="text-sm font-medium text-gray-700">Upstream</div>
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {upstreamLoading ? '...' : upstreamData?.total || 0}
                </div>
                <div className="text-xs text-gray-500 mt-1">Source columns</div>
              </Card>

              {/* Downstream Card */}
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="w-4 h-4 text-green-600" />
                  <div className="text-sm font-medium text-gray-700">Downstream</div>
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {downstreamLoading ? '...' : downstreamData?.total || 0}
                </div>
                <div className="text-xs text-gray-500 mt-1">Derived columns</div>
              </Card>
            </div>
          </Section>

          {/* Upstream Columns */}
          {upstreamColumns.length > 0 && (
            <Section title="Upstream Sources" icon={<TrendingUp className="w-4 h-4" />}>
              <div className="space-y-2">
                {upstreamColumns.map((col: any) => (
                  <ColumnItem
                    key={col.column_urn}
                    columnUrn={col.column_urn}
                    columnName={col.column_name}
                    capsuleName={col.capsule_name}
                    dataType={col.data_type}
                    transformationType={col.transformation_type}
                    confidence={col.confidence}
                    onClick={() => onNavigate?.(col.column_urn)}
                  />
                ))}
                {(upstreamData?.total || 0) > upstreamColumns.length && (
                  <div className="text-xs text-gray-500 text-center py-2">
                    +{(upstreamData?.total || 0) - upstreamColumns.length} more
                  </div>
                )}
              </div>
            </Section>
          )}

          {/* Downstream Columns */}
          {downstreamColumns.length > 0 && (
            <Section title="Downstream Targets" icon={<TrendingDown className="w-4 h-4" />}>
              <div className="space-y-2">
                {downstreamColumns.map((col: any) => (
                  <ColumnItem
                    key={col.column_urn}
                    columnUrn={col.column_urn}
                    columnName={col.column_name}
                    capsuleName={col.capsule_name}
                    dataType={col.data_type}
                    transformationType={col.transformation_type}
                    confidence={col.confidence}
                    onClick={() => onNavigate?.(col.column_urn)}
                  />
                ))}
                {(downstreamData?.total || 0) > downstreamColumns.length && (
                  <div className="text-xs text-gray-500 text-center py-2">
                    +{(downstreamData?.total || 0) - downstreamColumns.length} more
                  </div>
                )}
              </div>
            </Section>
          )}

          {/* Transformations */}
          {transformationList.length > 0 && (
            <Section title="Transformations" icon={<Code2 className="w-4 h-4" />}>
              <div className="space-y-3">
                {transformationList.map((transform: any, idx: number) => (
                  <TransformationItem key={idx} transformation={transform} />
                ))}
              </div>
            </Section>
          )}

          {/* No data message */}
          {upstreamColumns.length === 0 &&
            downstreamColumns.length === 0 &&
            transformationList.length === 0 && (
              <div className="text-center py-8">
                <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  No lineage data available for this column
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}

// Helper Components

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">{children}</div>;
}

function DataList({ children }: { children: React.ReactNode }) {
  return <div className="space-y-2">{children}</div>;
}

function DataItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-sm text-gray-600 flex-shrink-0">{label}:</span>
      <span className={`text-sm text-gray-900 text-right ${mono ? 'font-mono' : ''}`}>
        {value}
      </span>
    </div>
  );
}

function ColumnItem({
  columnUrn,
  columnName,
  capsuleName,
  dataType,
  transformationType,
  confidence,
  onClick,
}: {
  columnUrn: string;
  columnName: string;
  capsuleName: string;
  dataType?: string;
  transformationType?: string;
  confidence?: number;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full p-3 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors text-left"
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">{columnName}</div>
          <div className="text-xs text-gray-600 truncate">{capsuleName}</div>
        </div>
        {dataType && <div className="text-xs text-gray-500 flex-shrink-0">{dataType}</div>}
      </div>
      {transformationType && (
        <div className="flex items-center gap-2 mt-2">
          <TransformationBadge type={transformationType} />
          {confidence !== undefined && (
            <span className="text-xs text-gray-500">{Math.round(confidence * 100)}%</span>
          )}
        </div>
      )}
    </button>
  );
}

function TransformationItem({ transformation }: { transformation: any }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-start justify-between gap-2 mb-2">
        <TransformationBadge type={transformation.transformation_type} />
        {transformation.confidence !== undefined && (
          <span className="text-xs text-gray-500">
            {Math.round(transformation.confidence * 100)}% confidence
          </span>
        )}
      </div>
      {transformation.transformation_logic && (
        <div className="mt-2 p-2 bg-white rounded border border-gray-200">
          <code className="text-xs text-gray-700 font-mono break-all">
            {transformation.transformation_logic}
          </code>
        </div>
      )}
      <div className="mt-2 text-xs text-gray-500">
        Detected by: {transformation.detected_by || 'unknown'}
      </div>
    </div>
  );
}

function TransformationBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    identity: 'bg-blue-100 text-blue-700 border-blue-300',
    cast: 'bg-purple-100 text-purple-700 border-purple-300',
    aggregate: 'bg-orange-100 text-orange-700 border-orange-300',
    string_transform: 'bg-green-100 text-green-700 border-green-300',
    arithmetic: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    date_transform: 'bg-cyan-100 text-cyan-700 border-cyan-300',
    conditional: 'bg-red-100 text-red-700 border-red-300',
    formula: 'bg-pink-100 text-pink-700 border-pink-300',
    subquery: 'bg-indigo-100 text-indigo-700 border-indigo-300',
  };

  const colorClass = colors[type] || 'bg-gray-100 text-gray-700 border-gray-300';

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium border ${colorClass}`}>
      {type.replace('_', ' ')}
    </span>
  );
}
