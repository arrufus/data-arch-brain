/**
 * Badge Component
 *
 * Reusable badge for displaying labels with different variants.
 */

import { clsx } from 'clsx';

export type BadgeVariant =
  | 'bronze'
  | 'silver'
  | 'gold'
  | 'raw'
  | 'marts'
  | 'pii'
  | 'no-pii'
  | 'critical'
  | 'error'
  | 'warning'
  | 'info'
  | 'success'
  | 'default';

export type BadgeSize = 'sm' | 'md' | 'lg';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  // Medallion layers
  bronze: 'bg-amber-100 text-amber-800',
  silver: 'bg-slate-100 text-slate-800',
  gold: 'bg-yellow-100 text-yellow-800',
  raw: 'bg-gray-100 text-gray-800',
  marts: 'bg-purple-100 text-purple-800',

  // PII status
  pii: 'bg-red-100 text-red-800',
  'no-pii': 'bg-green-100 text-green-800',

  // Severity
  critical: 'bg-red-100 text-red-800',
  error: 'bg-orange-100 text-orange-800',
  warning: 'bg-yellow-100 text-yellow-800',
  info: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',

  // Default
  default: 'bg-gray-100 text-gray-800',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export default function Badge({ children, variant = 'default', size = 'sm', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {children}
    </span>
  );
}
