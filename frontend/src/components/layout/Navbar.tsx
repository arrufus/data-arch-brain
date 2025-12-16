'use client';

/**
 * Navbar Component
 *
 * Top navigation bar with app title, search, and user menu.
 */

import Link from 'next/link';
import { Database, Search, Settings, User } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-30 h-16">
      <div className="h-full px-4 flex items-center justify-between">
        {/* Logo and Title */}
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <Database className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Data Architecture Brain</h1>
            <p className="text-xs text-gray-500">Architecture Intelligence Platform</p>
          </div>
        </Link>

        {/* Search Bar (placeholder for now) */}
        <div className="flex-1 max-w-2xl mx-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search capsules, columns, domains..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled
            />
          </div>
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-4">
          <button
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
          <button
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            title="User Profile"
          >
            <User className="w-5 h-5" />
          </button>
        </div>
      </div>
    </nav>
  );
}
