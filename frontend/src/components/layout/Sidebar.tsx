'use client';

/**
 * Sidebar Component
 *
 * Left sidebar navigation with links to main features.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Database,
  Shield,
  CheckCircle,
  AlertTriangle,
  FolderTree,
  Package,
  Tag,
  FileText,
  GitBranch,
  Copy,
  Target,
  Settings,
} from 'lucide-react';
import { clsx } from 'clsx';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

const navItems: NavItem[] = [
  {
    href: '/',
    label: 'Dashboard',
    icon: <Home className="w-5 h-5" />,
  },
  {
    href: '/capsules',
    label: 'Data Capsules',
    icon: <Database className="w-5 h-5" />,
  },
  {
    href: '/compliance',
    label: 'PII Compliance',
    icon: <Shield className="w-5 h-5" />,
  },
  {
    href: '/conformance',
    label: 'Conformance',
    icon: <CheckCircle className="w-5 h-5" />,
  },
  {
    href: '/domains',
    label: 'Domains',
    icon: <FolderTree className="w-5 h-5" />,
  },
  {
    href: '/products',
    label: 'Data Products',
    icon: <Package className="w-5 h-5" />,
  },
  {
    href: '/tags',
    label: 'Tags',
    icon: <Tag className="w-5 h-5" />,
  },
  {
    href: '/lineage',
    label: 'Lineage Graph',
    icon: <GitBranch className="w-5 h-5" />,
  },
  {
    href: '/impact',
    label: 'Impact Analysis',
    icon: <Target className="w-5 h-5" />,
  },
  {
    href: '/redundancy',
    label: 'Redundancy',
    icon: <Copy className="w-5 h-5" />,
  },
  {
    href: '/reports',
    label: 'Reports',
    icon: <FileText className="w-5 h-5" />,
  },
  {
    href: '/settings',
    label: 'Settings',
    icon: <Settings className="w-5 h-5" />,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="bg-gray-50 border-r border-gray-200 fixed left-0 top-16 bottom-0 w-64 overflow-y-auto z-20">
      <nav className="p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group',
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
              )}
            >
              <span
                className={clsx(
                  'transition-colors',
                  isActive ? 'text-blue-600' : 'text-gray-500 group-hover:text-gray-700'
                )}
              >
                {item.icon}
              </span>
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="text-xs px-2 py-0.5 bg-gray-200 text-gray-600 rounded-full font-medium">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
