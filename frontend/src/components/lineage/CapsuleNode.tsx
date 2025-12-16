'use client';

/**
 * Custom Capsule Node for React Flow
 *
 * Renders a data capsule as a node in the lineage graph.
 */

import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Database, Shield, FileText, Package, Camera } from 'lucide-react';

interface CapsuleNodeData {
  name: string;
  type: string;
  layer: string | null;
  hasPii: boolean;
  color: string;
}

interface CapsuleNodeProps {
  data: CapsuleNodeData;
  sourcePosition?: Position;
  targetPosition?: Position;
}

function CapsuleNode({ data, sourcePosition, targetPosition }: CapsuleNodeProps) {
  const getIcon = () => {
    const iconClass = "w-4 h-4";
    switch (data.type) {
      case 'model':
        return <Database className={iconClass} />;
      case 'source':
        return <FileText className={iconClass} />;
      case 'seed':
        return <Package className={iconClass} />;
      case 'snapshot':
        return <Camera className={iconClass} />;
      default:
        return <Database className={iconClass} />;
    }
  };

  return (
    <div
      className="px-4 py-3 rounded-lg border-2 shadow-lg bg-white transition-all hover:shadow-xl cursor-pointer"
      style={{ borderColor: data.color, minWidth: 200 }}
    >
      {/* Target Handle (incoming edges) */}
      <Handle
        type="target"
        position={targetPosition || Position.Top}
        style={{ background: data.color, width: 10, height: 10 }}
      />

      {/* Node Content */}
      <div className="flex items-start gap-2">
        {/* Icon */}
        <div className="p-1.5 rounded flex-shrink-0" style={{ backgroundColor: `${data.color}20`, color: data.color }}>
          {getIcon()}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          {/* Name */}
          <div className="font-semibold text-gray-900 text-sm truncate">{data.name}</div>

          {/* Metadata */}
          <div className="flex items-center gap-2 mt-1">
            {/* Type Badge */}
            <span
              className="text-xs px-1.5 py-0.5 rounded font-medium"
              style={{ backgroundColor: `${data.color}20`, color: data.color }}
            >
              {data.type}
            </span>

            {/* Layer Badge */}
            {data.layer && (
              <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-gray-100 text-gray-700">
                {data.layer}
              </span>
            )}

            {/* PII Indicator */}
            {data.hasPii && (
              <div className="flex items-center gap-1 text-red-600">
                <Shield className="w-3 h-3" />
                <span className="text-xs font-medium">PII</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Source Handle (outgoing edges) */}
      <Handle
        type="source"
        position={sourcePosition || Position.Bottom}
        style={{ background: data.color, width: 10, height: 10 }}
      />
    </div>
  );
}

export default memo(CapsuleNode);
