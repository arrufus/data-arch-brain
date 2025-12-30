'use client';

/**
 * Task Impact Analysis Component (Phase 8)
 *
 * Main component for analyzing task-level impact of schema changes
 */

import { useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Info, TrendingUp } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import TaskImpactGraph from './TaskImpactGraph';
import TaskImpactSummary from './TaskImpactSummary';
import TaskImpactList from './TaskImpactList';

interface TaskImpactAnalysisProps {
  columnUrn: string;
  changeType: 'delete' | 'rename' | 'type_change' | 'nullability' | 'default';
  depth?: number;
}

interface TaskImpact {
  dag_id: string;
  task_id: string;
  dependency_type: string;
  risk_score: number;
  risk_level: string;
  criticality_score?: number;
  schedule_interval?: string;
}

interface DAGImpact {
  dag_id: string;
  affected_task_count: number;
  critical_task_count: number;
  max_risk_score: number;
  tasks: TaskImpact[];
}

interface TaskImpactResult {
  total_tasks: number;
  total_dags: number;
  critical_tasks: number;
  risk_level: string;
  confidence_score: number;
  tasks: TaskImpact[];
  dags: DAGImpact[];
  affected_columns: Array<{
    column_urn: string;
    capsule_urn?: string;
    data_type?: string;
  }>;
}

export default function TaskImpactAnalysis({
  columnUrn,
  changeType,
  depth = 5,
}: TaskImpactAnalysisProps) {
  const [impactResult, setImpactResult] = useState<TaskImpactResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'graph' | 'list'>('graph');

  const analyzeImpact = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post(
        `/api/v1/impact/analyze/column/${encodeURIComponent(columnUrn)}`,
        null,
        {
          params: {
            change_type: changeType,
            depth: depth,
          },
        }
      );

      setImpactResult(response.data);
    } catch (err: any) {
      const errorMessage = err?.message || err?.detail || 'Unknown error occurred';
      setError(errorMessage);
      console.error('Impact analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return <XCircle className="w-6 h-6 text-red-600" />;
      case 'high':
        return <AlertTriangle className="w-6 h-6 text-orange-600" />;
      case 'medium':
        return <Info className="w-6 h-6 text-yellow-600" />;
      case 'low':
        return <CheckCircle className="w-6 h-6 text-green-600" />;
      default:
        return <Info className="w-6 h-6 text-gray-600" />;
    }
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Task Impact Analysis</h2>
            <p className="text-sm text-gray-600 mt-1">
              Analyzing impact of <span className="font-medium">{changeType}</span> change on{' '}
              <span className="font-mono text-xs">{columnUrn}</span>
            </p>
          </div>
          <button
            onClick={analyzeImpact}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Analyzing...
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4" />
                Analyze Impact
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-300 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800 font-medium">Error</p>
          </div>
          <p className="text-red-700 text-sm mt-2">{error}</p>
        </div>
      )}

      {/* Results */}
      {impactResult && (
        <>
          {/* Summary Cards */}
          <TaskImpactSummary
            totalTasks={impactResult.total_tasks}
            totalDags={impactResult.total_dags}
            criticalTasks={impactResult.critical_tasks}
            riskLevel={impactResult.risk_level}
            confidenceScore={impactResult.confidence_score}
            getRiskIcon={getRiskIcon}
            getRiskColor={getRiskColor}
          />

          {/* View Toggle */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex gap-2">
              <button
                onClick={() => setView('graph')}
                className={`px-4 py-2 rounded-lg font-medium ${
                  view === 'graph'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Graph View
              </button>
              <button
                onClick={() => setView('list')}
                className={`px-4 py-2 rounded-lg font-medium ${
                  view === 'list'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                List View
              </button>
            </div>
          </div>

          {/* Impact Visualization */}
          {view === 'graph' ? (
            <TaskImpactGraph
              tasks={impactResult.tasks}
              dags={impactResult.dags}
              affectedColumns={impactResult.affected_columns}
            />
          ) : (
            <TaskImpactList
              tasks={impactResult.tasks}
              dags={impactResult.dags}
              getRiskColor={getRiskColor}
            />
          )}
        </>
      )}

      {/* Empty State */}
      {!loading && !error && !impactResult && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <Info className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Analysis Yet
          </h3>
          <p className="text-gray-600">
            Click "Analyze Impact" to see which Airflow tasks will be affected by this change.
          </p>
        </div>
      )}
    </div>
  );
}
