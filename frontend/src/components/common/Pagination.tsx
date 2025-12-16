/**
 * Pagination Component
 *
 * Pagination controls with page navigation.
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

interface PaginationProps {
  total: number;
  offset: number;
  limit: number;
  onPageChange: (newOffset: number) => void;
  className?: string;
}

export default function Pagination({ total, offset, limit, onPageChange, className }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const hasMore = offset + limit < total;
  const hasPrevious = offset > 0;

  const handlePrevious = () => {
    if (hasPrevious) {
      onPageChange(Math.max(0, offset - limit));
    }
  };

  const handleNext = () => {
    if (hasMore) {
      onPageChange(offset + limit);
    }
  };

  const handlePageClick = (page: number) => {
    onPageChange((page - 1) * limit);
  };

  // Generate page numbers to display (show current page and 2 pages before/after)
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxPagesToShow = 7;

    if (totalPages <= maxPagesToShow) {
      // Show all pages if total is small
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show first page
      pages.push(1);

      // Calculate range around current page
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      // Add ellipsis after first page if needed
      if (start > 2) {
        pages.push('...');
      }

      // Add pages around current page
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      // Add ellipsis before last page if needed
      if (end < totalPages - 1) {
        pages.push('...');
      }

      // Show last page
      pages.push(totalPages);
    }

    return pages;
  };

  if (total === 0) {
    return null;
  }

  return (
    <div className={clsx('flex items-center justify-between', className)}>
      {/* Info */}
      <div className="text-sm text-gray-700">
        Showing <span className="font-medium">{offset + 1}</span> to{' '}
        <span className="font-medium">{Math.min(offset + limit, total)}</span> of{' '}
        <span className="font-medium">{total}</span> results
      </div>

      {/* Page Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={handlePrevious}
          disabled={!hasPrevious}
          className={clsx(
            'p-2 rounded-lg border transition-colors',
            hasPrevious
              ? 'border-gray-300 text-gray-700 hover:bg-gray-50'
              : 'border-gray-200 text-gray-400 cursor-not-allowed'
          )}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        {/* Page Numbers */}
        <div className="flex items-center gap-1">
          {getPageNumbers().map((page, index) =>
            page === '...' ? (
              <span key={`ellipsis-${index}`} className="px-3 py-2 text-gray-500">
                ...
              </span>
            ) : (
              <button
                key={page}
                onClick={() => handlePageClick(page as number)}
                className={clsx(
                  'px-3 py-2 rounded-lg font-medium transition-colors',
                  page === currentPage
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                )}
              >
                {page}
              </button>
            )
          )}
        </div>

        <button
          onClick={handleNext}
          disabled={!hasMore}
          className={clsx(
            'p-2 rounded-lg border transition-colors',
            hasMore
              ? 'border-gray-300 text-gray-700 hover:bg-gray-50'
              : 'border-gray-200 text-gray-400 cursor-not-allowed'
          )}
          aria-label="Next page"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
