'use client';

/**
 * Column Lineage Graph Component (Phase 7)
 *
 * Interactive visualization of column-to-column lineage relationships
 */

import { useEffect, useMemo, useCallback, useRef, useImperativeHandle, forwardRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Panel,
  ReactFlowInstance,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useColumnLineage } from '@/lib/api/column-lineage';
import ColumnNode from './ColumnNode';
import { AlertCircle, Loader2 } from 'lucide-react';

interface ColumnLineageGraphProps {
  columnUrn: string;
  direction?: 'upstream' | 'downstream' | 'both';
  depth?: number;
  onNodeClick?: (columnUrn: string) => void;
}

export interface ColumnLineageGraphHandle {
  getNodes: () => Node[];
  getEdges: () => Edge[];
  getReactFlowInstance: () => ReactFlowInstance | null;
  getMetadata: () => Record<string, any>;
}

// Custom node types
const nodeTypes = {
  column: ColumnNode,
};

// Transform API data to React Flow format
function transformToGraphFormat(lineageData: any, focusedUrn: string) {
  if (!lineageData?.nodes) return { nodes: [], edges: [] };

  // Build adjacency lists for layout calculation
  const adjacency = new Map<string, Set<string>>();
  const reverseAdjacency = new Map<string, Set<string>>();

  lineageData.nodes.forEach((n: any) => {
    adjacency.set(n.column_urn, new Set());
    reverseAdjacency.set(n.column_urn, new Set());
  });

  lineageData.edges.forEach((e: any) => {
    adjacency.get(e.source_column_urn)?.add(e.target_column_urn);
    reverseAdjacency.get(e.target_column_urn)?.add(e.source_column_urn);
  });

  // Calculate levels (depth from focused node)
  const levels = new Map<string, number>();
  const visited = new Set<string>();

  function calculateLevels(urn: string, level: number, isUpstream: boolean) {
    if (visited.has(urn)) return;
    visited.add(urn);
    levels.set(urn, level);

    const neighbors = isUpstream
      ? reverseAdjacency.get(urn) || new Set()
      : adjacency.get(urn) || new Set();

    neighbors.forEach((neighbor) => {
      if (!visited.has(neighbor)) {
        calculateLevels(neighbor, level + 1, isUpstream);
      }
    });
  }

  // Start from focused node
  levels.set(focusedUrn, 0);
  visited.add(focusedUrn);

  // Calculate upstream levels (negative)
  reverseAdjacency.get(focusedUrn)?.forEach((upstream) => {
    calculateLevels(upstream, -1, true);
  });

  // Calculate downstream levels (positive)
  adjacency.get(focusedUrn)?.forEach((downstream) => {
    calculateLevels(downstream, 1, false);
  });

  // Group nodes by level for positioning
  const levelGroups = new Map<number, string[]>();
  levels.forEach((level, urn) => {
    if (!levelGroups.has(level)) {
      levelGroups.set(level, []);
    }
    levelGroups.get(level)!.push(urn);
  });

  // Create nodes with positions
  const nodes: Node[] = lineageData.nodes.map((node: any) => {
    const level = levels.get(node.column_urn) || 0;
    const levelNodes = levelGroups.get(level) || [];
    const indexInLevel = levelNodes.indexOf(node.column_urn);

    // Horizontal positioning
    const x = level * 350 + 400; // 350px spacing between levels, offset by 400
    // Vertical positioning
    const y = indexInLevel * 150 + 100; // 150px spacing between nodes in same level

    return {
      id: node.column_urn,
      type: 'column',
      position: { x, y },
      data: {
        column_name: node.column_name,
        data_type: node.data_type,
        capsule_name: node.capsule_name,
        capsule_urn: node.capsule_urn,
        transformation_type: node.transformation_type,
        transformation_logic: node.transformation_logic,
        confidence: node.confidence,
        depth: Math.abs(level),
        is_focused: node.column_urn === focusedUrn,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });

  // Create edges
  const edges: Edge[] = lineageData.edges.map((edge: any) => ({
    id: `${edge.source_column_urn}-${edge.target_column_urn}`,
    source: edge.source_column_urn,
    target: edge.target_column_urn,
    type: 'smoothstep',
    animated: edge.transformation_type === 'aggregate' || edge.transformation_type === 'formula',
    label: edge.transformation_type,
    labelStyle: { fontSize: 10, fontWeight: 500 },
    labelBgStyle: { fill: 'white' },
    style: {
      stroke: getEdgeColor(edge.transformation_type),
      strokeWidth: 2,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 20,
      height: 20,
      color: getEdgeColor(edge.transformation_type),
    },
  }));

  return { nodes, edges };
}

function getEdgeColor(transformationType?: string): string {
  const colors: Record<string, string> = {
    identity: '#3B82F6', // blue
    cast: '#A855F7', // purple
    aggregate: '#F97316', // orange
    string_transform: '#10B981', // green
    arithmetic: '#EAB308', // yellow
    date_transform: '#06B6D4', // cyan
    conditional: '#EF4444', // red
    formula: '#EC4899', // pink
    subquery: '#6366F1', // indigo
  };
  return colors[transformationType || 'identity'] || '#6B7280'; // gray default
}

function ColumnLineageGraphInner(
  { columnUrn, direction = 'both', depth = 3, onNodeClick }: ColumnLineageGraphProps,
  ref: React.Ref<ColumnLineageGraphHandle>
) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  // Fetch column lineage data
  const { data: lineageData, isLoading, error } = useColumnLineage(columnUrn, {
    direction,
    depth,
  });

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    getNodes: () => nodes,
    getEdges: () => edges,
    getReactFlowInstance: () => reactFlowInstance.current,
    getMetadata: () => ({
      columnUrn,
      direction,
      depth,
      timestamp: new Date().toISOString(),
      summary: lineageData?.summary || {},
    }),
  }));

  // Transform data to graph format when data changes
  useEffect(() => {
    if (lineageData?.nodes) {
      const { nodes: graphNodes, edges: graphEdges } = transformToGraphFormat(
        lineageData,
        columnUrn
      );
      setNodes(graphNodes);
      setEdges(graphEdges);
    }
  }, [lineageData, columnUrn, setNodes, setEdges]);

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Loading column lineage...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center max-w-md">
          <AlertCircle className="w-8 h-8 text-red-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-gray-900 mb-1">
            Failed to load column lineage
          </p>
          <p className="text-sm text-gray-600">
            {error instanceof Error ? error.message : 'An unknown error occurred'}
          </p>
        </div>
      </div>
    );
  }

  // No data state
  if (!lineageData?.nodes || lineageData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600">No lineage data available for this column</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full" id="column-lineage-graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onInit={(instance) => {
          reactFlowInstance.current = instance;
        }}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
      >
        <Background color="#e5e7eb" gap={16} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as any;
            if (data.is_focused) return '#3B82F6';
            if (data.transformation_type) return getEdgeColor(data.transformation_type);
            return '#9CA3AF';
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />

        {/* Info Panel */}
        <Panel position="top-left" className="bg-white p-3 rounded-lg shadow-md border border-gray-200">
          <div className="text-sm space-y-1">
            <div className="font-semibold text-gray-900">
              {lineageData.summary?.total_nodes || nodes.length} columns
            </div>
            <div className="text-gray-600">
              {lineageData.summary?.total_edges || edges.length} transformations
            </div>
            {lineageData.summary?.max_depth_reached && (
              <div className="text-gray-600">
                Max depth: {lineageData.summary.max_depth_reached}
              </div>
            )}
          </div>
        </Panel>

        {/* Legend Panel */}
        <Panel position="bottom-right" className="bg-white p-3 rounded-lg shadow-md border border-gray-200">
          <div className="text-xs font-semibold text-gray-700 mb-2">Transformations</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-gray-600">Identity</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span className="text-gray-600">Cast</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-orange-500" />
              <span className="text-gray-600">Aggregate</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-gray-600">String</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

const ColumnLineageGraph = forwardRef<ColumnLineageGraphHandle, ColumnLineageGraphProps>(
  ColumnLineageGraphInner
);
ColumnLineageGraph.displayName = 'ColumnLineageGraph';

export default ColumnLineageGraph;
