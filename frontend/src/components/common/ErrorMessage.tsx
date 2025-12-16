/**
 * Error Message Component
 *
 * Display error messages with retry functionality.
 */

import { AlertCircle, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorMessage({
  title = 'Error',
  message,
  onRetry,
  className,
}: ErrorMessageProps) {
  return (
    <div className={clsx('bg-red-50 border border-red-200 rounded-lg p-6', className)}>
      <div className="flex items-start gap-3">
        <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-red-900 mb-1">{title}</h3>
          <p className="text-sm text-red-700">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Inline Error Message (compact version)
 */
export function InlineError({ message, className }: { message: string; className?: string }) {
  return (
    <div className={clsx('flex items-center gap-2 text-red-600', className)}>
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      <span className="text-sm">{message}</span>
    </div>
  );
}
