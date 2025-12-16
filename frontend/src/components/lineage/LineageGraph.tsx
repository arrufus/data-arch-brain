'use client';

/**
 * Interactive Lineage Graph Component
 *
 * Uses React Flow to render an interactive data lineage graph.
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
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
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import Loading from '@/components/common/Loading';
import ErrorMessage from '@/components/common/ErrorMessage';
import CapsuleNode from './CapsuleNode';

interface LineageGraphProps {
  focusedCapsuleUrn: string | null;
  layoutDirection: 'TB' | 'LR';
}

interface LineageData {
  nodes: {
    urn: string;
    name: string;
    type: string;
    layer: string | null;
    has_pii: boolean;
  }[];
  edges: {
    source_urn: string;
    target_urn: string;
    edge_type: string;
  }[];
}

// Custom node types
const nodeTypes = {
  capsule: CapsuleNode,
};

export default function LineageGraph({ focusedCapsuleUrn, layoutDirection }: LineageGraphProps) {
  const router = useRouter();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Fetch lineage data
  const { data: lineageData, isLoading, error, refetch } = useQuery<LineageData>({
    queryKey: ['graph-lineage', focusedCapsuleUrn],
    queryFn: async () => {
      let url: string;
      if (focusedCapsuleUrn) {
        // Fetch focused lineage for specific capsule
        url = `/api/v1/graph/export/lineage/${encodeURIComponent(focusedCapsuleUrn)}?format=json&direction=both&depth=10`;
      } else {
        // Fetch full graph
        url = `/api/v1/graph/export?format=json`;
      }

      const response = await apiClient.get(url);

      // The JSON export endpoint returns { nodes: [...], edges: [...] }
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Layout algorithm - Dagre-like hierarchical layout
  const calculateLayout = useCallback((graphNodes: any[], graphEdges: any[]) => {
    if (!graphNodes.length) return { nodes: [], edges: [] };

    // Build adjacency list
    const adjacency = new Map<string, Set<string>>();
    graphNodes.forEach(n => adjacency.set(n.urn, new Set()));
    graphEdges.forEach(e => {
      if (adjacency.has(e.source_urn)) {
        adjacency.get(e.source_urn)!.add(e.target_urn);
      }
    });

    // Calculate node levels using topological sort
    const levels = new Map<string, number>();
    const visited = new Set<string>();

    const calculateLevel = (urn: string, level: number = 0): number => {
      if (visited.has(urn)) return levels.get(urn) || 0;
      visited.add(urn);

      const children = adjacency.get(urn);
      let maxChildLevel = level;

      if (children) {
        children.forEach(childUrn => {
          const childLevel = calculateLevel(childUrn, level + 1);
          maxChildLevel = Math.max(maxChildLevel, childLevel);
        });
      }

      const nodeLevel = level;
      const existingLevel = levels.get(urn);
      if (existingLevel === undefined || nodeLevel > existingLevel) {
        levels.set(urn, nodeLevel);
      }

      return maxChildLevel;
    };

    // Find root nodes (nodes with no incoming edges)
    const incomingEdges = new Set(graphEdges.map(e => e.target_urn));
    const rootNodes = graphNodes.filter(n => !incomingEdges.has(n.urn));

    // Calculate levels from all roots
    rootNodes.forEach(root => calculateLevel(root.urn, 0));

    // Group nodes by level
    const nodesByLevel = new Map<number, any[]>();
    graphNodes.forEach(node => {
      const level = levels.get(node.urn) || 0;
      if (!nodesByLevel.has(level)) {
        nodesByLevel.set(level, []);
      }
      nodesByLevel.get(level)!.push(node);
    });

    // Position nodes
    const nodeWidth = 250;
    const nodeHeight = 80;
    const horizontalGap = 100;
    const verticalGap = 150;

    const flowNodes: Node[] = graphNodes.map(node => {
      const level = levels.get(node.urn) || 0;
      const nodesAtLevel = nodesByLevel.get(level) || [];
      const indexInLevel = nodesAtLevel.indexOf(node);

      let x, y;
      if (layoutDirection === 'LR') {
        // Left to Right layout
        x = level * (nodeWidth + horizontalGap);
        y = indexInLevel * (nodeHeight + verticalGap);
      } else {
        // Top to Bottom layout
        x = indexInLevel * (nodeWidth + horizontalGap);
        y = level * (nodeHeight + verticalGap);
      }

      // Color by type
      const typeColors: Record<string, string> = {
        model: '#3B82F6',
        source: '#10B981',
        seed: '#8B5CF6',
        snapshot: '#F59E0B',
        analysis: '#EF4444',
      };

      return {
        id: node.urn,
        type: 'capsule',
        position: { x, y },
        data: {
          name: node.name,
          type: node.type,
          layer: node.layer,
          hasPii: node.has_pii,
          color: typeColors[node.type] || '#6B7280',
        },
        sourcePosition: layoutDirection === 'LR' ? Position.Right : Position.Bottom,
        targetPosition: layoutDirection === 'LR' ? Position.Left : Position.Top,
      };
    });

    const flowEdges: Edge[] = graphEdges.map((edge, index) => ({
      id: `${edge.source_urn}-${edge.target_urn}-${index}`,
      source: edge.source_urn,
      target: edge.target_urn,
      type: 'smoothstep',
      animated: true,
      label: edge.edge_type,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 20,
        height: 20,
      },
      style: { stroke: '#94A3B8', strokeWidth: 2 },
      labelStyle: { fill: '#64748B', fontSize: 10, fontWeight: 500 },
      labelBgStyle: { fill: '#F8FAFC' },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [layoutDirection]);

  // Update graph when data changes
  useEffect(() => {
    if (lineageData) {
      const { nodes: flowNodes, edges: flowEdges } = calculateLayout(
        lineageData.nodes,
        lineageData.edges
      );
      setNodes(flowNodes);
      setEdges(flowEdges);
    }
  }, [lineageData, calculateLayout, setNodes, setEdges]);

  // Handle node click - navigate to capsule detail
  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      router.push(`/capsules/${encodeURIComponent(node.id)}`);
    },
    [router]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loading text="Loading lineage graph..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <ErrorMessage
          title="Failed to load lineage"
          message={error?.message || 'Unknown error'}
          onRetry={refetch}
        />
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-gray-500 text-lg mb-2">No lineage data available</p>
          <p className="text-gray-400 text-sm">
            Ingest data to see the lineage graph
          </p>
        </div>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={onNodeClick}
      nodeTypes={nodeTypes}
      fitView
      attributionPosition="bottom-left"
      minZoom={0.1}
      maxZoom={2}
    >
      <Background gap={16} size={1} />
      <Controls />
      <MiniMap
        nodeColor={(node) => (node.data as any).color || '#6B7280'}
        nodeStrokeWidth={3}
        zoomable
        pannable
      />
    </ReactFlow>
  );
}
