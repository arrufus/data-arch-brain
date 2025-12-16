/**
 * Footer Component
 *
 * Simple footer with version and links.
 */

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-gray-200 py-4 px-6 text-center text-sm text-gray-600">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <span>© {currentYear} Data Architecture Brain</span>
          <span className="text-gray-400">|</span>
          <span className="text-gray-500">v1.0.0-beta</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="/docs" className="text-blue-600 hover:text-blue-800 transition-colors">
            Documentation
          </a>
          <a
            href="http://localhost:8002/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 transition-colors"
          >
            API Docs
          </a>
          <a
            href="http://localhost:8002/health"
            target="_blank"
            rel="noopener noreferrer"
            className="text-green-600 hover:text-green-800 transition-colors"
          >
            API Status
          </a>
        </div>
      </div>
    </footer>
  );
}
