'use client';

/**
 * Task Impact Graph Component (Phase 8)
 *
 * React Flow visualization of task-level impact
 */

import { useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface TaskImpactGraphProps {
  tasks: Array<{
    dag_id: string;
    task_id: string;
    risk_level: string;
    risk_score: number;
  }>;
  dags: Array<{
    dag_id: string;
    affected_task_count: number;
    max_risk_score: number;
  }>;
  affectedColumns: Array<{
    column_urn: string;
    capsule_urn?: string;
  }>;
}

export default function TaskImpactGraph({
  tasks,
  dags,
  affectedColumns,
}: TaskImpactGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Transform data to graph format
  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    // Create DAG nodes (left column)
    dags.forEach((dag, index) => {
      const dagColor =
        dag.max_risk_score >= 75 ? '#DC2626' :
        dag.max_risk_score >= 50 ? '#EA580C' :
        dag.max_risk_score >= 25 ? '#CA8A04' :
        '#16A34A';

      newNodes.push({
        id: `dag-${dag.dag_id}`,
        type: 'default',
        data: {
          label: (
            <div className="text-center">
              <div className="font-bold">{dag.dag_id}</div>
              <div className="text-xs text-gray-600">
                {dag.affected_task_count} tasks
              </div>
              <div className="text-xs font-medium" style={{ color: dagColor }}>
                Risk: {dag.max_risk_score.toFixed(0)}
              </div>
            </div>
          ),
        },
        position: { x: 50, y: index * 150 + 50 },
        style: {
          background: '#fff',
          border: `2px solid ${dagColor}`,
          borderRadius: '8px',
          padding: '12px',
          minWidth: '200px',
        },
      });
    });

    // Create task nodes (middle column) - group by DAG
    const dagTaskMap = new Map<string, typeof tasks>();
    tasks.forEach((task) => {
      if (!dagTaskMap.has(task.dag_id)) {
        dagTaskMap.set(task.dag_id, []);
      }
      dagTaskMap.get(task.dag_id)!.push(task);
    });

    let taskYOffset = 0;
    let taskGlobalIndex = 0;
    dagTaskMap.forEach((dagTasks, dagId) => {
      dagTasks.forEach((task, taskIndex) => {
        const taskColor =
          task.risk_level === 'critical' ? '#DC2626' :
          task.risk_level === 'high' ? '#EA580C' :
          task.risk_level === 'medium' ? '#CA8A04' :
          '#16A34A';

        const taskId = `task-${task.dag_id}-${task.task_id}`;

        newNodes.push({
          id: taskId,
          type: 'default',
          data: {
            label: (
              <div className="text-center">
                <div className="font-medium text-sm">{task.task_id}</div>
                <div className="text-xs" style={{ color: taskColor }}>
                  {task.risk_level.toUpperCase()}
                </div>
                <div className="text-xs text-gray-600">
                  {task.risk_score.toFixed(0)}
                </div>
              </div>
            ),
          },
          position: { x: 350, y: taskYOffset + taskIndex * 100 },
          style: {
            background: '#fff',
            border: `2px solid ${taskColor}`,
            borderRadius: '6px',
            padding: '8px',
            minWidth: '150px',
          },
        });

        // Edge from DAG to Task - use global index to ensure uniqueness
        newEdges.push({
          id: `edge-dag-task-${taskGlobalIndex}`,
          source: `dag-${dagId}`,
          target: taskId,
          animated: task.risk_level === 'critical',
          style: { stroke: taskColor, strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: taskColor,
          },
        });

        taskGlobalIndex++;
      });

      taskYOffset += dagTasks.length * 100 + 50;
    });

    // Create column nodes (right column) - show subset
    const columnsToShow = affectedColumns.slice(0, 10);
    columnsToShow.forEach((column, index) => {
      const columnId = `column-${index}`;
      const columnName = column.column_urn.split(':').pop() || column.column_urn;

      newNodes.push({
        id: columnId,
        type: 'default',
        data: {
          label: (
            <div className="text-center">
              <div className="text-xs font-mono">{columnName}</div>
            </div>
          ),
        },
        position: { x: 650, y: index * 80 + 50 },
        style: {
          background: '#F3F4F6',
          border: '1px solid #9CA3AF',
          borderRadius: '4px',
          padding: '6px',
          fontSize: '11px',
        },
      });

      // Connect a few tasks to columns (simplified)
      if (index < tasks.length) {
        const task = tasks[index];
        newEdges.push({
          id: `edge-task-column-${index}`,
          source: `task-${task.dag_id}-${task.task_id}`,
          target: columnId,
          style: { stroke: '#9CA3AF', strokeWidth: 1, strokeDasharray: '5,5' },
        });
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [tasks, dags, affectedColumns, setNodes, setEdges]);

  return (
    <div className="bg-white rounded-lg shadow" style={{ height: '600px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <Background />
        <MiniMap
          nodeColor={(node) => {
            const borderColor = node.style?.border as string;
            return borderColor?.match(/#[0-9A-F]{6}/i)?.[0] || '#6B7280';
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  );
}
