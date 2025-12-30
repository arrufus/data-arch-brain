'use client';

/**
 * Task Impact Summary Component (Phase 8)
 *
 * Displays summary statistics for task impact analysis
 */

interface TaskImpactSummaryProps {
  totalTasks: number;
  totalDags: number;
  criticalTasks: number;
  riskLevel: string;
  confidenceScore: number;
  getRiskIcon: (level: string) => React.ReactNode;
  getRiskColor: (level: string) => string;
}

export default function TaskImpactSummary({
  totalTasks,
  totalDags,
  criticalTasks,
  riskLevel,
  confidenceScore,
  getRiskIcon,
  getRiskColor,
}: TaskImpactSummaryProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
      {/* Overall Risk */}
      <div className={`rounded-lg border-2 p-6 ${getRiskColor(riskLevel)}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium opacity-80">Overall Risk</p>
            <p className="text-2xl font-bold mt-1 capitalize">{riskLevel}</p>
          </div>
          {getRiskIcon(riskLevel)}
        </div>
      </div>

      {/* Total Tasks */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-sm font-medium text-gray-600">Affected Tasks</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">{totalTasks}</p>
        <p className="text-xs text-gray-500 mt-1">tasks impacted</p>
      </div>

      {/* Total DAGs */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-sm font-medium text-gray-600">Affected DAGs</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">{totalDags}</p>
        <p className="text-xs text-gray-500 mt-1">pipelines impacted</p>
      </div>

      {/* Critical Tasks */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-sm font-medium text-gray-600">Critical Tasks</p>
        <p className="text-3xl font-bold text-orange-600 mt-1">{criticalTasks}</p>
        <p className="text-xs text-gray-500 mt-1">high/critical risk</p>
      </div>

      {/* Confidence Score */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-sm font-medium text-gray-600">Confidence</p>
        <p className="text-3xl font-bold text-blue-600 mt-1">
          {(confidenceScore * 100).toFixed(0)}%
        </p>
        <p className="text-xs text-gray-500 mt-1">prediction confidence</p>
      </div>
    </div>
  );
}
