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

## Available screen

The agents page lists definitions from `GET /api/v1/agents`, supports client-side search and refresh, and loads agent configuration on demand from `GET /api/v1/agents/{id}`. JSON create, edit, and delete actions use `POST`, `PATCH`, and `DELETE` on `/api/v1/agents`. Runtime availability is not exposed by the current API, so the interface reports definitions as configured.
