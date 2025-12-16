/**
 * Loading Component
 *
 * Loading spinner for async operations.
 */

import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export default function Loading({ size = 'md', text, className }: LoadingProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center gap-2', className)}>
      <Loader2 className={clsx('animate-spin text-blue-600', sizeClasses[size])} />
      {text && <p className="text-sm text-gray-600">{text}</p>}
    </div>
  );
}

/**
 * Loading Spinner (inline version)
 */
export function LoadingSpinner({ size = 'sm', className }: Pick<LoadingProps, 'size' | 'className'>) {
  return <Loader2 className={clsx('animate-spin text-blue-600', sizeClasses[size], className)} />;
}

/**
 * Loading Skeleton (placeholder)
 */
export function LoadingSkeleton({ className }: { className?: string }) {
  return <div className={clsx('animate-pulse bg-gray-200 rounded', className)} />;
}
