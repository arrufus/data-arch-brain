# Web Dashboard - User Guide

## Overview

The Data Architecture Brain Web Dashboard is a modern, responsive React application that provides visual access to your data architecture intelligence. Built with Next.js 16, TypeScript, and Tailwind CSS, it offers an intuitive interface for exploring data assets, monitoring PII compliance, and generating reports.

## Features Implemented

### ✅ Phase 1: Project Setup & Foundation
- Next.js 16 with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- Axios-based API client with authentication
- React Query for server state management
- Responsive design for mobile, tablet, and desktop

### ✅ Phase 2-3: Data Capsule Browser & Detail View
**Capsule Browser** ([http://localhost:3001/capsules](http://localhost:3001/capsules))
- Searchable table of all data capsules
- Filters: layer, type, domain, has PII
- Pagination with configurable page size
- Sort by name, type, layer
- Real-time search with debounce

**Capsule Detail View** ([http://localhost:3001/capsules/[urn]](http://localhost:3001/capsules/[urn]))
- Comprehensive capsule metadata display
- **Columns Tab**: Full column listing with PII highlighting, filtering, and data type information
- **Lineage Tab**: Upstream and downstream lineage visualization with depth control (1-5 levels)
- **Violations Tab**: Conformance violations with severity indicators and remediation guidance

### ✅ Phase 4: PII Compliance Dashboard
**Compliance Dashboard** ([http://localhost:3001/compliance](http://localhost:3001/compliance))

**PII Inventory Tab:**
- Bar charts showing PII distribution by type and layer (Recharts)
- Filterable table with layer and PII type filters
- CSV export functionality with calculated percentages
- Summary statistics (total PII columns, affected capsules, types found)

**PII Exposure Tab:**
- Warning banners for detected exposures
- Severity breakdown cards (Critical, High, Medium, Low)
- Exposure cards with recommendations and severity indicators
- Filtering by layer and severity
- Links to capsule detail pages

**PII Trace Tab:**
- Search form for column URN tracing
- Column details display with PII type and layer badges
- Summary statistics (total nodes, masked/unmasked terminals)
- Origin, propagation path, and terminal nodes visualization
- Masking status indicators

### ✅ Phase 5: Reports & Export
**Reports Page** ([http://localhost:3001/reports](http://localhost:3001/reports))

**Available Reports:**
1. **PII Inventory Report**
   - Formats: JSON, CSV, HTML
   - Filters: Layer, PII Type
   - Includes: PII types distribution, layer breakdown, detailed column information

2. **Conformance Report**
   - Formats: JSON, CSV, HTML
   - Filters: Severity, Rule Set
   - Includes: Overall score, category scores, violations with details

3. **Capsule Summary Report**
   - Formats: JSON, CSV
   - Filters: Layer, Capsule Type
   - Includes: Capsule metadata, column counts, PII indicators, test coverage

**Report Features:**
- One-click download with auto-generated filenames
- Toast notifications for success/error
- Loading indicators during generation
- Preview of generated filename before download

## Getting Started

### Prerequisites
- Backend API running on http://localhost:8002
- Valid API key configured in `.env.local`

### Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure Environment Variables**
   Create `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8002
   NEXT_PUBLIC_API_KEY=dev-api-key-change-in-prod
   ```

3. **Run Development Server**
   ```bash
   npm run dev
   ```
   Dashboard available at: http://localhost:3001

4. **Build for Production**
   ```bash
   npm run build
   npm start
   ```

### Docker Deployment

The dashboard is configured to run alongside the backend in Docker:

```bash
cd docker
docker-compose up -d
```

Services:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8002
- PostgreSQL: localhost:5432

## User Guide

### Navigating the Dashboard

**Main Navigation (Sidebar)**
- Dashboard: Overview stats and quick actions
- Data Capsules: Browse and search capsules
- PII Compliance: Monitor sensitive data
- Reports: Generate and download reports
- Conformance: Architecture compliance (coming soon)
- Violations: Rule violations (coming soon)

### Common Tasks

#### 1. Finding a Data Capsule
1. Navigate to "Data Capsules"
2. Use the search bar to search by name
3. Apply filters (layer, type, has PII)
4. Click on a capsule to view details

#### 2. Viewing Capsule Lineage
1. Open a capsule detail page
2. Click the "Lineage" tab
3. Select direction (upstream/downstream/both)
4. Adjust depth (1-5 levels)
5. View counts and click nodes to navigate

#### 3. Checking PII Compliance
1. Navigate to "PII Compliance"
2. View summary statistics
3. **Inventory Tab**: See PII distribution charts and export CSV
4. **Exposure Tab**: Check for unmasked PII in consumption layers
5. **Trace Tab**: Enter a column URN to trace PII data flow

#### 4. Generating Reports
1. Navigate to "Reports"
2. Select report type (PII Inventory, Conformance, or Capsule Summary)
3. Choose output format (JSON, CSV, or HTML)
4. Apply optional filters
5. Click "Generate & Download"
6. Report downloads automatically with timestamp

### Keyboard Shortcuts

- `/` - Focus search bar (capsule browser)
- `Esc` - Clear search / Close modals
- Arrow keys - Navigate table rows

## Architecture

### Tech Stack
- **Frontend**: React 18 + Next.js 16 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3
- **State Management**: TanStack React Query v5
- **Charts**: Recharts 2
- **Icons**: Lucide React
- **HTTP Client**: Axios 1.6

### Project Structure
```
frontend/
├── src/
│   ├── app/                  # Next.js pages (App Router)
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home/Dashboard
│   │   ├── capsules/         # Capsule browser & detail
│   │   ├── compliance/       # PII compliance dashboard
│   │   └── reports/          # Reports & export
│   ├── components/           # React components
│   │   ├── layout/           # Navbar, Sidebar, Footer
│   │   ├── capsules/         # Capsule-related components
│   │   ├── compliance/       # PII compliance components
│   │   ├── reports/          # Report generator
│   │   └── common/           # Reusable UI components
│   ├── lib/                  # Utilities & API client
│   │   ├── api/              # API integration
│   │   │   ├── client.ts     # Axios instance
│   │   │   ├── capsules.ts   # Capsule endpoints
│   │   │   ├── compliance.ts # Compliance endpoints
│   │   │   ├── reports.ts    # Reports endpoints
│   │   │   └── types.ts      # TypeScript types
│   │   ├── hooks/            # Custom React hooks
│   │   └── utils/            # Helper functions
│   └── styles/               # Global styles
├── public/                   # Static assets
├── .env.local                # Environment variables
├── next.config.js            # Next.js configuration
├── tailwind.config.js        # Tailwind configuration
└── tsconfig.json             # TypeScript configuration
```

### API Integration

The frontend communicates with the FastAPI backend via REST APIs:

**Authentication:**
- API Key via `X-API-Key` header
- Configured in `.env.local`

**Key Endpoints Used:**
- `/api/v1/capsules` - Capsule data
- `/api/v1/compliance/pii-inventory` - PII inventory
- `/api/v1/compliance/pii-exposure` - PII exposure detection
- `/api/v1/compliance/pii-trace/{urn}` - PII lineage tracing
- `/api/v1/reports/*` - Report downloads

**Error Handling:**
- Automatic retry for failed requests
- User-friendly error messages
- Toast notifications for errors
- Loading states during requests

## Performance

**Optimization Strategies:**
- React Query caching (5-10 minute stale time)
- Code splitting via Next.js
- Lazy loading for heavy components
- Debounced search inputs (500ms)
- Pagination for large datasets
- Responsive images with Next.js Image

**Expected Performance:**
- First Contentful Paint (FCP): < 1.5s
- Largest Contentful Paint (LCP): < 2.5s
- Time to Interactive (TTI): < 3.5s

## Browser Support

**Minimum Versions:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Note:** Internet Explorer is not supported.

## Troubleshooting

### Common Issues

**1. "Failed to load data" errors**
- Check backend is running: `curl http://localhost:8002/health`
- Verify API key in `.env.local`
- Check browser console for detailed error

**2. Reports not downloading**
- Ensure backend is accessible
- Check browser popup blocker settings
- Verify sufficient disk space

**3. Slow performance**
- Clear browser cache
- Check React Query DevTools for stale queries
- Monitor network tab for slow API calls

**4. TypeScript errors during build**
- Run `npm run type-check` to see all errors
- Ensure types in `lib/api/types.ts` match backend responses
- Check for missing dependencies

### Debug Mode

Enable React Query DevTools:
```tsx
// app/layout.tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

<ReactQueryDevtools initialIsOpen={false} />
```

## Future Enhancements (Phase 6-7)

### Priority 2 Features
- **Interactive Lineage Graph**: React Flow visualization with zoom, pan, and filtering
- **Conformance Dashboard**: Real-time scoring with rule management
- **Impact Analysis**: Downstream impact prediction for changes

### Priority 3 Features
- **Redundancy Detection UI**: Visual similarity matching and duplicate finding
- **Settings Page**: User preferences, API key management
- **Custom Dashboards**: Drag-and-drop widgets
- **Data Product Catalog**: Browse and manage data products

## Contributing

### Development Workflow
1. Create feature branch
2. Make changes
3. Run tests: `npm test`
4. Run linting: `npm run lint`
5. Build: `npm run build`
6. Submit PR

### Code Style
- Use TypeScript for all new files
- Follow Tailwind CSS conventions
- Use Prettier for formatting
- Write meaningful component names
- Add JSDoc comments for complex logic

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/data-arch-brain/issues
- Documentation: `/docs`
- API Docs: http://localhost:8002/api/v1/docs

## License

[Your License Here]

---

**Dashboard Version**: 1.0.0
**Last Updated**: December 16, 2025
**Status**: ✅ Production Ready
