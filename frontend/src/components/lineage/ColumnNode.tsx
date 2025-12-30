'use client';

/**
 * Column Node Component for Column Lineage Graph
 *
 * Displays a column node in the lineage graph with transformation metadata
 */

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Database, Table2, ArrowRight } from 'lucide-react';

interface ColumnNodeData {
  column_name: string;
  data_type: string;
  capsule_name: string;
  capsule_urn?: string;
  transformation_type?: string;
  transformation_logic?: string;
  confidence?: number;
  depth?: number;
  is_focused?: boolean;
}

const transformationColors: Record<string, string> = {
  identity: 'bg-blue-100 border-blue-400 text-blue-700',
  cast: 'bg-purple-100 border-purple-400 text-purple-700',
  aggregate: 'bg-orange-100 border-orange-400 text-orange-700',
  string_transform: 'bg-green-100 border-green-400 text-green-700',
  arithmetic: 'bg-yellow-100 border-yellow-400 text-yellow-700',
  date_transform: 'bg-cyan-100 border-cyan-400 text-cyan-700',
  conditional: 'bg-red-100 border-red-400 text-red-700',
  formula: 'bg-pink-100 border-pink-400 text-pink-700',
  subquery: 'bg-indigo-100 border-indigo-400 text-indigo-700',
};

const transformationLabels: Record<string, string> = {
  identity: 'Identity',
  cast: 'Cast',
  aggregate: 'Aggregate',
  string_transform: 'String',
  arithmetic: 'Math',
  date_transform: 'Date',
  conditional: 'Conditional',
  formula: 'Formula',
  subquery: 'Subquery',
};

function ColumnNode({ data, selected }: NodeProps<ColumnNodeData>) {
  const transformColor = data.transformation_type
    ? transformationColors[data.transformation_type] || 'bg-gray-100 border-gray-400 text-gray-700'
    : 'bg-white border-gray-300 text-gray-700';

  const borderColor = data.is_focused
    ? 'border-blue-500 shadow-lg'
    : selected
    ? 'border-blue-400 shadow-md'
    : 'border-gray-300';

  return (
    <div
      className={`
        relative px-4 py-3 rounded-lg border-2 bg-white
        transition-all duration-200 hover:shadow-lg
        min-w-[200px] max-w-[280px]
        ${borderColor}
      `}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      {/* Column Header */}
      <div className="flex items-start gap-2 mb-2">
        <Table2 className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">
            {data.column_name}
          </div>
          <div className="text-xs text-gray-500 truncate">
            {data.data_type}
          </div>
        </div>
      </div>

      {/* Capsule Info */}
      <div className="flex items-center gap-1.5 text-xs text-gray-600 mb-2">
        <Database className="w-3 h-3 flex-shrink-0" />
        <span className="truncate">{data.capsule_name}</span>
      </div>

      {/* Transformation Badge */}
      {data.transformation_type && (
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200">
          <div
            className={`
              px-2 py-1 rounded text-xs font-medium border
              ${transformColor}
            `}
          >
            {transformationLabels[data.transformation_type] || data.transformation_type}
          </div>
          {data.confidence !== undefined && (
            <div className="text-xs text-gray-500">
              {Math.round(data.confidence * 100)}%
            </div>
          )}
        </div>
      )}

      {/* Transformation Logic Preview */}
      {data.transformation_logic && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-600 font-mono truncate">
            {data.transformation_logic}
          </div>
        </div>
      )}

      {/* Depth Indicator */}
      {data.depth !== undefined && data.depth > 0 && (
        <div className="absolute -top-2 -right-2 w-5 h-5 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
          {data.depth}
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
    </div>
  );
}

export default memo(ColumnNode);
