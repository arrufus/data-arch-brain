'use client';

/**
 * Home/Dashboard Page
 *
 * Landing page with overview stats and quick links.
 */

import Link from 'next/link';
import { Database, Shield, CheckCircle, AlertTriangle, FileText, GitBranch } from 'lucide-react';
import { useCapsuleStats } from '@/lib/api/capsules';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { LoadingSkeleton } from '@/components/common/Loading';
import { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api/health';

export default function Home() {
  // Fetch capsule stats
  const { data: capsuleStats, isLoading: isLoadingCapsuleStats } = useCapsuleStats();

  // Fetch PII inventory summary
  const { data: piiData, isLoading: isLoadingPII } = useQuery({
    queryKey: ['pii-inventory'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/compliance/pii-inventory');
      return response.data;
    },
  });

  // Fetch conformance violations summary
  const { data: violationsData, isLoading: isLoadingViolations } = useQuery({
    queryKey: ['violations-summary'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/violations', {
        params: { status: 'open', limit: 1 },
      });
      return response.data;
    },
  });

  // System health check
  const [healthStatus, setHealthStatus] = useState<{
    api: 'checking' | 'healthy' | 'error';
    database: 'checking' | 'healthy' | 'error';
    cache: 'checking' | 'healthy' | 'error';
  }>({
    api: 'checking',
    database: 'checking',
    cache: 'checking',
  });

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await getHealth();
        setHealthStatus({
          api: 'healthy',
          database: 'healthy',
          cache: 'healthy',
        });
      } catch (error) {
        setHealthStatus({
          api: 'error',
          database: 'error',
          cache: 'error',
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome to Data Architecture Brain - Your architecture intelligence platform
        </p>
      </div>

      {/* Quick Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Data Capsules"
          value={isLoadingCapsuleStats ? null : capsuleStats?.total_capsules}
          icon={<Database className="w-6 h-6" />}
          color="blue"
          href="/capsules"
          isLoading={isLoadingCapsuleStats}
        />
        <StatCard
          title="PII Columns"
          value={isLoadingPII ? null : piiData?.summary?.total_pii_columns}
          icon={<Shield className="w-6 h-6" />}
          color="red"
          href="/compliance"
          isLoading={isLoadingPII}
        />
        <StatCard
          title="Conformance Score"
          value="N/A"
          icon={<CheckCircle className="w-6 h-6" />}
          color="green"
          href="/conformance"
          isLoading={false}
        />
        <StatCard
          title="Open Violations"
          value={isLoadingViolations ? null : violationsData?.pagination?.total}
          icon={<AlertTriangle className="w-6 h-6" />}
          color="orange"
          href="/violations"
          isLoading={isLoadingViolations}
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionCard
            title="Browse Capsules"
            description="Explore your data assets"
            icon={<Database className="w-5 h-5" />}
            href="/capsules"
          />
          <ActionCard
            title="View PII Compliance"
            description="Check sensitive data exposure"
            icon={<Shield className="w-5 h-5" />}
            href="/compliance"
          />
          <ActionCard
            title="Generate Reports"
            description="Download analysis reports"
            icon={<FileText className="w-5 h-5" />}
            href="/reports"
          />
          <ActionCard
            title="Check Violations"
            description="Review conformance issues"
            icon={<AlertTriangle className="w-5 h-5" />}
            href="/violations"
          />
          <ActionCard
            title="Explore Lineage"
            description="Trace data flow (Coming Soon)"
            icon={<GitBranch className="w-5 h-5" />}
            href="/lineage"
            badge="P2"
          />
          <ActionCard
            title="API Documentation"
            description="View REST API docs"
            icon={<FileText className="w-5 h-5" />}
            href="http://localhost:8002/api/v1/docs"
            external
          />
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="space-y-2">
          <StatusItem
            label="Backend API"
            status={healthStatus.api}
          />
          <StatusItem
            label="Database"
            status={healthStatus.database}
          />
          <StatusItem
            label="Cache"
            status={healthStatus.cache}
          />
        </div>
      </div>
    </div>
  );
}

// Component: Stat Card
function StatCard({
  title,
  value,
  icon,
  color,
  href,
  isLoading,
}: {
  title: string;
  value: number | string | null | undefined;
  icon: React.ReactNode;
  color: 'blue' | 'red' | 'green' | 'orange';
  href: string;
  isLoading: boolean;
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    red: 'bg-red-50 text-red-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <Link
      href={href}
      className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">{title}</p>
          {isLoading ? (
            <LoadingSkeleton className="h-8 w-20 mt-1" />
          ) : (
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {value ?? 0}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </Link>
  );
}

// Component: Action Card
function ActionCard({
  title,
  description,
  icon,
  href,
  badge,
  external,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  badge?: string;
  external?: boolean;
}) {
  const content = (
    <>
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">{icon}</div>
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">{title}</h3>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
        {badge && (
          <span className="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded-full font-medium">
            {badge}
          </span>
        )}
      </div>
    </>
  );

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
      >
        {content}
      </a>
    );
  }

  return (
    <Link
      href={href}
      className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
    >
      {content}
    </Link>
  );
}

// Component: Status Item
function StatusItem({
  label,
  status,
}: {
  label: string;
  status: 'checking' | 'healthy' | 'error';
}) {
  const statusConfig = {
    checking: {
      text: 'Checking...',
      className: 'text-gray-500',
      dot: 'bg-gray-400',
    },
    healthy: {
      text: 'Healthy',
      className: 'text-green-600',
      dot: 'bg-green-500',
    },
    error: {
      text: 'Error',
      className: 'text-red-600',
      dot: 'bg-red-500',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-gray-700">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${config.dot}`} />
        <span className={`text-sm font-medium ${config.className}`}>{config.text}</span>
      </div>
    </div>
  );
}
