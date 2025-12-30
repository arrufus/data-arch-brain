'use client';

/**
 * Task Impact List Component (Phase 8)
 *
 * Table/list view of impacted tasks grouped by DAG
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, Clock, TrendingUp } from 'lucide-react';

interface TaskImpactListProps {
  tasks: Array<{
    dag_id: string;
    task_id: string;
    dependency_type: string;
    risk_score: number;
    risk_level: string;
    schedule_interval?: string;
    criticality_score?: number;
    success_rate?: number;
  }>;
  dags: Array<{
    dag_id: string;
    affected_task_count: number;
    critical_task_count: number;
    max_risk_score: number;
    avg_risk_score: number;
    tasks: any[];
  }>;
  getRiskColor: (level: string) => string;
}

export default function TaskImpactList({
  tasks,
  dags,
  getRiskColor,
}: TaskImpactListProps) {
  const [expandedDags, setExpandedDags] = useState<Set<string>>(new Set());

  const toggleDag = (dagId: string) => {
    const newExpanded = new Set(expandedDags);
    if (newExpanded.has(dagId)) {
      newExpanded.delete(dagId);
    } else {
      newExpanded.add(dagId);
    }
    setExpandedDags(newExpanded);
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-bold text-gray-900">Affected DAGs and Tasks</h3>
        <p className="text-sm text-gray-600 mt-1">
          Click on a DAG to expand and see individual tasks
        </p>
      </div>

      <div className="divide-y divide-gray-200">
        {dags.map((dag) => {
          const isExpanded = expandedDags.has(dag.dag_id);

          return (
            <div key={dag.dag_id}>
              {/* DAG Row */}
              <div
                className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => toggleDag(dag.dag_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                    <div>
                      <h4 className="font-bold text-gray-900">{dag.dag_id}</h4>
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                        <span>{dag.affected_task_count} tasks</span>
                        {dag.critical_task_count > 0 && (
                          <span className="flex items-center gap-1 text-orange-600">
                            <AlertTriangle className="w-4 h-4" />
                            {dag.critical_task_count} critical
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-sm text-gray-600">Max Risk</div>
                      <div className="text-lg font-bold text-gray-900">
                        {dag.max_risk_score.toFixed(0)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-600">Avg Risk</div>
                      <div className="text-lg font-bold text-gray-900">
                        {dag.avg_risk_score.toFixed(0)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tasks (expanded) */}
              {isExpanded && (
                <div className="bg-gray-50 px-6 py-2">
                  <div className="space-y-2">
                    {dag.tasks.map((task) => (
                      <div
                        key={task.task_id}
                        className="bg-white rounded-lg border border-gray-200 p-4"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h5 className="font-medium text-gray-900">
                                {task.task_id}
                              </h5>
                              <span
                                className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(
                                  task.risk_level
                                )}`}
                              >
                                {task.risk_level.toUpperCase()}
                              </span>
                              <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                {task.dependency_type}
                              </span>
                            </div>

                            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                              {task.schedule_interval && (
                                <span className="flex items-center gap-1">
                                  <Clock className="w-4 h-4" />
                                  {task.schedule_interval}
                                </span>
                              )}
                              {task.criticality_score !== null && (
                                <span className="flex items-center gap-1">
                                  <TrendingUp className="w-4 h-4" />
                                  Criticality: {(task.criticality_score * 100).toFixed(0)}%
                                </span>
                              )}
                              {task.success_rate !== null && (
                                <span>
                                  Success Rate: {task.success_rate.toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="text-right">
                            <div className="text-sm text-gray-600">Risk Score</div>
                            <div className="text-2xl font-bold text-gray-900">
                              {task.risk_score.toFixed(0)}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {dags.length === 0 && (
        <div className="px-6 py-12 text-center text-gray-500">
          No DAGs affected by this change
        </div>
      )}
    </div>
  );
}
