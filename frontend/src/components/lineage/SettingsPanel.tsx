'use client';

/**
 * Settings Panel Component (Phase 7.5)
 *
 * Allows users to customize lineage visualization settings
 */

import { useState, useEffect } from 'react';
import { X, Settings, Check } from 'lucide-react';

interface SettingsPanelProps {
  onClose: () => void;
  settings: LineageSettings;
  onSettingsChange: (settings: LineageSettings) => void;
}

export interface LineageSettings {
  showMiniMap: boolean;
  showControls: boolean;
  showLegend: boolean;
  showInfoPanel: boolean;
  animateEdges: boolean;
  nodeSpacing: number;
  levelSpacing: number;
  theme: 'light' | 'dark' | 'auto';
}

export const defaultSettings: LineageSettings = {
  showMiniMap: true,
  showControls: true,
  showLegend: true,
  showInfoPanel: true,
  animateEdges: true,
  nodeSpacing: 150,
  levelSpacing: 350,
  theme: 'light',
};

export default function SettingsPanel({ onClose, settings, onSettingsChange }: SettingsPanelProps) {
  const [localSettings, setLocalSettings] = useState<LineageSettings>(settings);

  // Update local settings when props change
  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleToggle = (key: keyof LineageSettings) => {
    const newSettings = { ...localSettings, [key]: !localSettings[key] };
    setLocalSettings(newSettings);
    onSettingsChange(newSettings);
  };

  const handleSliderChange = (key: keyof LineageSettings, value: number) => {
    const newSettings = { ...localSettings, [key]: value };
    setLocalSettings(newSettings);
    onSettingsChange(newSettings);
  };

  const handleThemeChange = (theme: 'light' | 'dark' | 'auto') => {
    const newSettings = { ...localSettings, theme };
    setLocalSettings(newSettings);
    onSettingsChange(newSettings);
  };

  const handleReset = () => {
    setLocalSettings(defaultSettings);
    onSettingsChange(defaultSettings);
  };

  return (
    <div className="fixed right-0 top-0 h-full w-[400px] bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-gray-600" />
          <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Display Options */}
        <Section title="Display Options">
          <ToggleSetting
            label="Show Mini Map"
            description="Display miniature overview of the graph"
            checked={localSettings.showMiniMap}
            onChange={() => handleToggle('showMiniMap')}
          />
          <ToggleSetting
            label="Show Controls"
            description="Display zoom and pan controls"
            checked={localSettings.showControls}
            onChange={() => handleToggle('showControls')}
          />
          <ToggleSetting
            label="Show Legend"
            description="Display transformation type legend"
            checked={localSettings.showLegend}
            onChange={() => handleToggle('showLegend')}
          />
          <ToggleSetting
            label="Show Info Panel"
            description="Display graph statistics panel"
            checked={localSettings.showInfoPanel}
            onChange={() => handleToggle('showInfoPanel')}
          />
        </Section>

        {/* Animation */}
        <Section title="Animation">
          <ToggleSetting
            label="Animate Edges"
            description="Animate edges for complex transformations"
            checked={localSettings.animateEdges}
            onChange={() => handleToggle('animateEdges')}
          />
        </Section>

        {/* Layout */}
        <Section title="Layout">
          <SliderSetting
            label="Node Spacing"
            description="Vertical spacing between nodes"
            value={localSettings.nodeSpacing}
            min={100}
            max={300}
            step={10}
            unit="px"
            onChange={(value) => handleSliderChange('nodeSpacing', value)}
          />
          <SliderSetting
            label="Level Spacing"
            description="Horizontal spacing between levels"
            value={localSettings.levelSpacing}
            min={200}
            max={500}
            step={50}
            unit="px"
            onChange={(value) => handleSliderChange('levelSpacing', value)}
          />
        </Section>

        {/* Theme */}
        <Section title="Theme">
          <div className="space-y-2">
            <ThemeOption
              label="Light"
              value="light"
              selected={localSettings.theme === 'light'}
              onChange={() => handleThemeChange('light')}
            />
            <ThemeOption
              label="Dark"
              value="dark"
              selected={localSettings.theme === 'dark'}
              onChange={() => handleThemeChange('dark')}
            />
            <ThemeOption
              label="Auto (System)"
              value="auto"
              selected={localSettings.theme === 'auto'}
              onChange={() => handleThemeChange('auto')}
            />
          </div>
        </Section>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
        <button
          onClick={handleReset}
          className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
        >
          Reset to Defaults
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  );
}

// Helper Components

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-900 mb-3">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function ToggleSetting({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-900">{label}</div>
        <div className="text-xs text-gray-600 mt-0.5">{description}</div>
      </div>
      <button
        onClick={onChange}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}
        `}
        role="switch"
        aria-checked={checked}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0
            transition duration-200 ease-in-out
            ${checked ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>
    </div>
  );
}

function SliderSetting({
  label,
  description,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-sm font-medium text-gray-900">{label}</div>
          <div className="text-xs text-gray-600 mt-0.5">{description}</div>
        </div>
        <div className="text-sm font-medium text-gray-900">
          {value}
          {unit}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
      />
    </div>
  );
}

function ThemeOption({
  label,
  value,
  selected,
  onChange,
}: {
  label: string;
  value: string;
  selected: boolean;
  onChange: () => void;
}) {
  return (
    <button
      onClick={onChange}
      className={`
        w-full px-4 py-3 rounded-lg border-2 transition-colors text-left flex items-center justify-between
        ${
          selected
            ? 'border-blue-600 bg-blue-50'
            : 'border-gray-200 bg-white hover:border-gray-300'
        }
      `}
    >
      <span className={`text-sm font-medium ${selected ? 'text-blue-900' : 'text-gray-900'}`}>
        {label}
      </span>
      {selected && <Check className="w-5 h-5 text-blue-600" />}
    </button>
  );
}
