# tempr frontend

React and TypeScript workspace for managing AI agent versions, planning and generating tests, inspecting execution traces, and comparing evaluation results. Built with Vite, Tailwind CSS, and shadcn/ui primitives. See the [product walkthrough](../README.md) for screenshots.

## Run locally

Requires Node.js 20.x or 22+ and npm. First follow the [backend setup guide](../backend/README.md) to install Python dependencies, configure `OPENAI_API_KEY`, run migrations, and start the API at `http://localhost:8000`.

In a separate terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173` (or the URL Vite prints if that port is busy). The app opens the **Agents** page. A new database starts empty; select **New agent** to get started.

The development server proxies `/api`, `/docs`, and `/openapi.json` to the backend. Default local setup needs no frontend environment file. Keep the backend and frontend running in separate terminals.

## Use the workspace

1. **Register an agent.** Select **New agent**, use **Example** to load a sample JSON body, and replace its name and configuration with your agent's details. **Format** formats the JSON; saving validates it through the API.
2. **Inspect and version.** Open the agent and select **View configuration** to review prompts, model settings, and tools. Use **New version** to save a revised configuration. Versions are immutable; agent names can be changed with **Rename**.
3. **Plan tests.** Select **Generate classification** to see the suggested allocation of test cases across eight categories. These percentages represent testing priorities. **Regenerate** refreshes the recommendation.
4. **Generate scenarios.** Select **Test suite** on a version, choose 1–100 questions (default 20), and select **Generate test suite**. An unclassified version is classified first. Review each question and its acceptance criteria. Regenerating replaces the suite and removes its trace and evaluation.
5. **Supply executions and start evaluation.** Run the cases in your own agent runtime. Upload their traces and start evaluation through the [backend API workflow](../backend/README.md#4-run-cases-and-upload-a-trace). These actions currently use the API; the workspace displays their results.
6. **Review results.** The test-suite page polls active jobs and shows completed scores and explanations for adherence, consistency, and grounding. Select **View trace & response** to inspect the recorded execution, final answer, and raw JSON.
7. **Compare revisions.** Select **Compare** on a version to make it the reference, then use **+** to add other versions. Expand categories to see the three rubric dimensions; arrows show score changes relative to the reference. Each version's scores reflect its own generated suite.

**Remove** removes an agent from the workspace. The theme selector supports light, dark, and system appearance.

## Configuration

For overrides, copy `.env.example` to `.env.local` in `frontend/`. Restart Vite after changes; deployment settings must be present when building.

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Backend target for Vite's development and preview proxies. |
| `VITE_API_BASE_URL` | Empty | API origin. Requests append `/api/v1`, so omit that suffix from this value. Empty uses the frontend's origin. |
| `VITE_API_DOCS_URL` | `/docs` | Target for the **API Docs** link. Set separately when hosting the API elsewhere. |

Keep provider credentials such as `OPENAI_API_KEY` in the backend environment. `VITE_*` values are exposed to the browser.

## Build and host

```bash
npm run build
npm run preview
```

The build type-checks the app and writes the production bundle to `dist/`. Preview serves that bundle locally at the URL printed by Vite and inherits the configured API proxy, so keep the backend running. A deployed static bundle needs its own routing configuration.

For hosting, serve `dist/` with:

- A fallback to `index.html` for workspace routes, including `/agents`, `/agents/:agentId`, `/agents/:agentId/compare`, and `/agents/:agentId/versions/:versionId/test-suite`.
- A reverse proxy for `/api/v1/*` to the backend when using the default, empty API base URL. Also proxy `/docs` and `/openapi.json` for the default **API Docs** link.

If using a separate API origin, set `VITE_API_BASE_URL` and `VITE_API_DOCS_URL` before building and configure CORS at the backend or gateway. The backend currently has no CORS middleware. Prefer the same-origin proxy setup for local use and deployments that do not need separate origins.

## Troubleshooting

- **API unavailable:** check that the backend is running and `http://localhost:8000/ready` responds. Confirm the proxy target and run backend migrations if requests report missing tables.
- **Classification or generation fails:** check the backend key, model settings, and returned error. An **API connected** indicator confirms agent-list access, not that provider credentials work.
- **No evaluation results yet:** complete generation, upload executions for every case, and start evaluation through the API. For interrupted or failed jobs, follow the [backend troubleshooting guide](../backend/README.md#troubleshooting).
- **API calls fail after hosting:** configure the production proxy or API origin; `VITE_API_PROXY_TARGET` configures Vite's local servers, not the deployed static bundle.

## Development checks

Run these from `frontend/`:

```bash
npm test
npm run check
npm run build
```

`npm test` runs Vitest once. `npm run check` runs Biome lint and formatting checks; `npm run check:ci` provides CI validation. Use `npm run lint` for lint only, `npm run fix` for safe fixes and formatting, or `npm run format` for formatting only. See the [repository guide](../README.md#git-hooks) to enable pre-commit checks.
