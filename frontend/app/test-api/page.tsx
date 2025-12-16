'use client';

/**
 * API Test Page
 *
 * Simple page to test API client connectivity and authentication.
 */

import { useState } from 'react';
import { getHealth, getLiveness, getReadiness } from '@/lib/api/health';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function TestAPIPage() {
  const [healthStatus, setHealthStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [healthData, setHealthData] = useState<any>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [livenessStatus, setLivenessStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [livenessData, setLivenessData] = useState<any>(null);

  const [readinessStatus, setReadinessStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [readinessData, setReadinessData] = useState<any>(null);

  const testHealth = async () => {
    setHealthStatus('loading');
    setHealthError(null);
    try {
      const data = await getHealth();
      setHealthData(data);
      setHealthStatus('success');
    } catch (error: any) {
      setHealthError(error.message || 'Unknown error');
      setHealthStatus('error');
    }
  };

  const testLiveness = async () => {
    setLivenessStatus('loading');
    try {
      const data = await getLiveness();
      setLivenessData(data);
      setLivenessStatus('success');
    } catch (error) {
      setLivenessStatus('error');
    }
  };

  const testReadiness = async () => {
    setReadinessStatus('loading');
    try {
      const data = await getReadiness();
      setReadinessData(data);
      setReadinessStatus('success');
    } catch (error) {
      setReadinessStatus('error');
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">API Client Test</h1>
        <p className="mt-2 text-gray-600">Test API connectivity and authentication</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Health Test (requires auth) */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Health Check (Auth)</h2>
          <button
            onClick={testHealth}
            disabled={healthStatus === 'loading'}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {healthStatus === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
            Test Health Endpoint
          </button>

          {healthStatus === 'success' && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-700 mb-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Success!</span>
              </div>
              <pre className="text-xs text-gray-700 overflow-auto">
                {JSON.stringify(healthData, null, 2)}
              </pre>
            </div>
          )}

          {healthStatus === 'error' && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 text-red-700 mb-2">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Error</span>
              </div>
              <p className="text-sm text-red-600">{healthError}</p>
            </div>
          )}
        </div>

        {/* Liveness Test (no auth) */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Liveness Check (No Auth)</h2>
          <button
            onClick={testLiveness}
            disabled={livenessStatus === 'loading'}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {livenessStatus === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
            Test Liveness
          </button>

          {livenessStatus === 'success' && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-700 mb-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Success!</span>
              </div>
              <pre className="text-xs text-gray-700 overflow-auto">
                {JSON.stringify(livenessData, null, 2)}
              </pre>
            </div>
          )}

          {livenessStatus === 'error' && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 text-red-700">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Error</span>
              </div>
            </div>
          )}
        </div>

        {/* Readiness Test (no auth) */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Readiness Check (No Auth)</h2>
          <button
            onClick={testReadiness}
            disabled={readinessStatus === 'loading'}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {readinessStatus === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
            Test Readiness
          </button>

          {readinessStatus === 'success' && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-700 mb-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Success!</span>
              </div>
              <pre className="text-xs text-gray-700 overflow-auto">
                {JSON.stringify(readinessData, null, 2)}
              </pre>
            </div>
          )}

          {readinessStatus === 'error' && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 text-red-700">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Error</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Configuration Info */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Configuration</h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between py-2 border-b">
            <span className="text-gray-600">API URL</span>
            <span className="font-mono text-gray-900">{process.env.NEXT_PUBLIC_API_URL || 'Not set'}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b">
            <span className="text-gray-600">API Key</span>
            <span className="font-mono text-gray-900">
              {process.env.NEXT_PUBLIC_API_KEY ? '✓ Configured' : '✗ Not set'}
            </span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-gray-600">Environment</span>
            <span className="font-mono text-gray-900">{process.env.NODE_ENV}</span>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-2">Testing Instructions</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li>• <strong>Health Check</strong>: Tests authenticated endpoint (requires X-API-Key header)</li>
          <li>• <strong>Liveness & Readiness</strong>: Test unauthenticated endpoints</li>
          <li>• Open browser DevTools (Console & Network tabs) to inspect requests</li>
          <li>• If health check fails with 401, check your API key in .env.local</li>
          <li>• If connection fails, ensure FastAPI backend is running on port 8002</li>
        </ul>
      </div>
    </div>
  );
}
