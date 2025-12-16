'use client';

/**
 * Client-side Providers Component
 *
 * Wraps the application with React Query Provider for server state management.
 * Must be a client component due to React Query's use of React context.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';

export default function Providers({ children }: { children: React.ReactNode }) {
  // Create QueryClient instance per request (Next.js best practice)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Stale time: data is considered fresh for 5 minutes
            staleTime: 5 * 60 * 1000,
            // Cache time: unused data stays in cache for 10 minutes
            gcTime: 10 * 60 * 1000,
            // Retry failed requests 1 time
            retry: 1,
            // Refetch on window focus in production
            refetchOnWindowFocus: process.env.NODE_ENV === 'production',
          },
          mutations: {
            // Retry failed mutations 0 times (user should retry manually)
            retry: 0,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Show React Query Devtools in development */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} position="bottom" />
      )}
    </QueryClientProvider>
  );
}
