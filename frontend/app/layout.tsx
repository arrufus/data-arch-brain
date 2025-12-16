import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import Navbar from '@/components/layout/Navbar';
import Sidebar from '@/components/layout/Sidebar';
import Footer from '@/components/layout/Footer';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Data Architecture Brain',
  description: 'Architecture Intelligence Platform - Analyze your data landscape',
  keywords: ['data architecture', 'data governance', 'PII compliance', 'data lineage', 'dbt'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased bg-gray-50">
        <Providers>
          {/* Navbar - Fixed at top */}
          <Navbar />

          {/* Sidebar - Fixed on left */}
          <Sidebar />

          {/* Main Content Area - Offset for navbar and sidebar */}
          <main className="ml-64 mt-16 min-h-screen p-6">
            <div className="max-w-7xl mx-auto">{children}</div>
          </main>

          {/* Footer - At bottom */}
          <div className="ml-64">
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
