# Tempr frontend

React, TypeScript, Vite, Tailwind CSS, and shadcn/ui primitives for the Tempr agent workspace.

## Run locally

Install dependencies and start the API and frontend in separate terminals:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/api` requests to `http://localhost:8000`.

## Configuration

Copy `.env.example` to `.env.local` to override settings. `VITE_API_PROXY_TARGET` changes the development proxy destination. `VITE_API_BASE_URL` sets an API origin for deployments; leave it blank to use same-origin `/api/v1` routes. `VITE_API_DOCS_URL` sets the Swagger UI link and defaults to `/docs`.

## Workspace

The versioned workspace uses `/agents`, `/agents/:agentId`, `/agents/:agentId/compare`, and `/agents/:agentId/versions/:versionId/test-suite`. It supports agent creation, rename, removal, immutable version creation, configuration inspection, classification comparisons, and version-specific test suite generation and review through the `/api/v1/agents` endpoints.

Deployments must serve `index.html` as the fallback for these frontend routes while continuing to proxy `/api/v1/*` to the backend; Vite's development server already provides this fallback.

Run `npm test` for the frontend interaction tests, `npm run build` for the production bundle, and `npm run lint` for static checks.
