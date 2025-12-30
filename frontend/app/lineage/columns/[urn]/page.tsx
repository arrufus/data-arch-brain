'use client';

/**
 * Column Lineage Page (Phase 7)
 *
 * Displays interactive column-level lineage graph
 */

import { use, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ColumnLineageGraph, {
  ColumnLineageGraphHandle,
} from '@/components/lineage/ColumnLineageGraph';
import ColumnDetailPanel from '@/components/lineage/ColumnDetailPanel';
import SettingsPanel, {
  LineageSettings,
  defaultSettings,
} from '@/components/lineage/SettingsPanel';
import { exportLineageGraph } from '@/lib/export/lineage-export';
import { ArrowLeft, Download, Maximize2, Settings, Info, FileJson, Image } from 'lucide-react';

interface PageProps {
  params: Promise<{ urn: string }>;
}

export default function ColumnLineagePage({ params }: PageProps) {
  const resolvedParams = use(params);
  const router = useRouter();
  const columnUrn = decodeURIComponent(resolvedParams.urn);
  const graphRef = useRef<ColumnLineageGraphHandle>(null);

  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both');
  const [depth, setDepth] = useState(3);
  const [selectedColumnUrn, setSelectedColumnUrn] = useState<string | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showSettingsPanel, setShowSettingsPanel] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [settings, setSettings] = useState<LineageSettings>(defaultSettings);

  // Extract column name from URN for display
  const columnName = columnUrn.split(':').pop() || columnUrn;

  const handleNodeClick = (clickedUrn: string) => {
    // Show detail panel for clicked column
    setSelectedColumnUrn(clickedUrn);
    setShowDetailPanel(true);
  };

  const handleNavigateToColumn = (newColumnUrn: string) => {
    // Navigate to the clicked column's lineage page
    setShowDetailPanel(false);
    router.push(`/lineage/columns/${encodeURIComponent(newColumnUrn)}`);
  };

  const handleExport = async (format: 'png' | 'svg' | 'json') => {
    if (!graphRef.current) return;

    setIsExporting(true);
    setShowExportMenu(false);

    try {
      const nodes = graphRef.current.getNodes();
      const edges = graphRef.current.getEdges();
      const reactFlowInstance = graphRef.current.getReactFlowInstance();
      const metadata = graphRef.current.getMetadata();

      await exportLineageGraph(
        { format, filename: `column-lineage-${columnName}-${Date.now()}` },
        {
          nodes,
          edges,
          reactFlowInstance,
          elementId: 'column-lineage-graph',
          metadata,
        }
      );
    } catch (error) {
      console.error('Export failed:', error);
      alert(error instanceof Error ? error.message : 'Failed to export graph');
    } finally {
      setIsExporting(false);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Go back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div>
            <h1 className="text-xl font-semibold text-gray-900">Column Lineage</h1>
            <p className="text-sm text-gray-600 font-mono">{columnName}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4">
          {/* Direction Control */}
          <div className="hidden md:flex items-center gap-2">
            <label className="text-sm text-gray-600">Direction:</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as any)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="both">Both</option>
              <option value="upstream">Upstream</option>
              <option value="downstream">Downstream</option>
            </select>
          </div>

          {/* Mobile Direction Control */}
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as any)}
            className="md:hidden px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="both">Both</option>
            <option value="upstream">Up</option>
            <option value="downstream">Down</option>
          </select>

          {/* Depth Control */}
          <div className="hidden md:flex items-center gap-2">
            <label className="text-sm text-gray-600">Depth:</label>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </div>

          {/* Mobile Depth Control */}
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="md:hidden px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="5">5</option>
            <option value="10">10</option>
          </select>

          {/* Action Buttons */}
          <button
            onClick={() => {
              setSelectedColumnUrn(columnUrn);
              setShowDetailPanel(true);
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Show column details"
          >
            <Info className="w-5 h-5" />
          </button>

          {/* Export Menu */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={isExporting}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              title="Export graph"
            >
              <Download className="w-5 h-5" />
            </button>

            {showExportMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowExportMenu(false)}
                />
                <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
                  <div className="py-1">
                    <button
                      onClick={() => handleExport('png')}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                    >
                      <Image className="w-4 h-4" />
                      Export as PNG
                    </button>
                    <button
                      onClick={() => handleExport('svg')}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                    >
                      <Image className="w-4 h-4" />
                      Export as SVG
                    </button>
                    <button
                      onClick={() => handleExport('json')}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                    >
                      <FileJson className="w-4 h-4" />
                      Export as JSON
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            <Maximize2 className="w-5 h-5" />
          </button>

          <button
            onClick={() => setShowSettingsPanel(true)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 bg-gray-50">
        <ColumnLineageGraph
          ref={graphRef}
          columnUrn={columnUrn}
          direction={direction}
          depth={depth}
          onNodeClick={handleNodeClick}
        />
      </div>

      {/* Detail Panel */}
      {showDetailPanel && selectedColumnUrn && (
        <ColumnDetailPanel
          columnUrn={selectedColumnUrn}
          onClose={() => setShowDetailPanel(false)}
          onNavigate={handleNavigateToColumn}
        />
      )}

      {/* Settings Panel */}
      {showSettingsPanel && (
        <SettingsPanel
          settings={settings}
          onSettingsChange={setSettings}
          onClose={() => setShowSettingsPanel(false)}
        />
      )}

      {/* Footer Info */}
      <div className="px-4 md:px-6 py-3 border-t bg-white">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 text-sm text-gray-600">
          <div className="truncate">
            <span className="font-medium">URN:</span> <span className="font-mono text-xs">{columnUrn}</span>
          </div>
          <div className="hidden md:flex items-center gap-4">
            <span>Click on nodes to explore further</span>
            <span>•</span>
            <span>Scroll to zoom</span>
            <span>•</span>
            <span>Drag to pan</span>
          </div>
          <div className="md:hidden text-xs">
            Click nodes • Scroll zoom • Drag pan
          </div>
        </div>
      </div>
    </div>
  );
}
