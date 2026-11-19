# tempr

**Understand your AI agents. Test their limits. Measure what improves.**

## Quickstart

Install [Docker Desktop](https://docs.docker.com/get-started/get-docker/) or Docker Engine with the Compose plugin, then run from the repository root:

```bash
cp .env.example .env
# Set OPENAI_API_KEY in .env to enable classification, test generation, and evaluation.
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). The app starts without an API key; agent management and saved-data browsing work, while AI-powered features need one. Compose uses `backend/data/app.db` directly, so it shares data with a local backend run and keeps it across restarts. Stop the app with `Ctrl+C` or `docker compose down`.

tempr is a platform for evaluating AI agents, taking teams from an agent definition to a focused test plan, generated scenarios, and explained evaluation results. It brings configuration history, testing priorities, execution evidence, and version comparisons into one workspace.

For businesses putting AI agents to work, the central question is whether those agents behave reliably when requests become difficult, incomplete, or adversarial. tempr helps teams investigate that question and use the findings to improve their agents before deployment.

## Why tempr matters

- **Less manual test design.** Generate scenarios and acceptance criteria from the prompts, model settings, and tools that define each agent.
- **Visibility into behavior.** Inspect responses, tool interactions, and scoring explanations to understand where an agent succeeds or needs attention.
- **Evidence for release decisions.** Compare versions across ordinary tasks and challenging scenarios to spot improvements and regressions.

## From agent definition to evaluation

The screenshots below walk through the workflow using a general assistant, a customer-support agent, and a pull-request reviewer.

### 1. Start with your agent workspace

The **Agents** page is the starting point. Search for an existing agent, check its latest version and classification status, or select **New agent** to register an agent and its initial configuration as JSON. Agents can also be registered through the API.

This gives teams a shared place to review the agents they are developing, from customer support to software review.

![Agents page showing Northstar Shop Support, Pull Request Reviewer Agent, and Friendly Helper with their latest versions and classification status](docs/images/welcome-screen.png)

### 2. Establish a version to test

Open an agent to see its current version, purpose, model, tools, and version history. Each saved version preserves an immutable configuration, so teams can trace results back to the definition being tested. Use **New version** when changing prompts, model settings, or tools.

Before classification, the workspace offers **Generate classification** as the next step toward a test plan.

![Friendly Helper workspace before classification, showing version 1.0 and the Generate classification action](docs/images/agent-workspace-before-classification.png)

### 3. Inspect the agent's instructions and capabilities

Select **View configuration** to inspect a version's model settings, system and developer prompts, and tool definitions. This is the context tempr uses to plan tests tailored to the agent's responsibilities.

In the customer-support example, the configuration defines order verification, policy lookup, and rules for protecting customer information. These instructions provide the basis for testing both useful behavior and potential failures.

![Version 1.1 configuration drawer showing model settings, customer-support prompts, and tool definitions](docs/images/version-configuration.png)

### 4. Turn the definition into testing priorities

Select **Generate classification** to have an LLM analyze the version and recommend how to distribute test cases across eight categories: happy paths, boundary probes, missing information, ambiguous inputs, prompt injection, policy bypass, sensitive data requests, and hallucination probes.

The allocation totals 100% and is saved per version. It describes the suggested share of test cases in each category; evaluation scores come later, after executions have been assessed. Use **Regenerate** to refresh the recommendation.

The support-agent example allocates the largest share to prompt injection, alongside everyday support tasks and attempts to bypass policy.

![Classified Northstar Shop Support workspace showing testing allocations across eight categories and its version history](docs/images/agent-workspace-after-classification.png)

### 5. Generate concrete test scenarios

Select **Test suite** on a version, choose between 1 and 100 questions, and select **Generate test suite**. The default is 20. tempr distributes the questions according to the saved testing allocation and generates a question and expected behavior for each case. If the version has not been classified, this flow classifies it first.

Review the resulting questions and acceptance criteria to understand what the agent will be assessed against. In the reviewer example, a happy-path test asks the agent to inspect a pull request, gather supporting evidence, and return actionable findings tied to changed code.

![Generated 20-test suite for Pull Request Reviewer Agent, showing happy-path questions and acceptance criteria](docs/images/test-suite-screen.png)

### 6. Evaluate executions and inspect the evidence

Run the generated cases in your agent's own runtime, then upload the execution traces through tempr's API and start an evaluation. Each suite case must have a corresponding execution. The [backend guide](backend/README.md) documents the trace format and evaluation endpoints.

An LLM judge assesses each execution against the test's expected behavior and returns scores with explanations:

| Dimension | What it assesses |
| --- | --- |
| Adherence | Did the agent meet the test's expected behavior? |
| Consistency | Were its responses and actions consistent within the execution? |
| Grounding | Were its claims supported by information available to it? |

Results appear in the test suite. Select **View trace & response** to inspect the final answer, ordered execution steps, tool interactions, and raw JSON alongside the scores.

The trace below shows a prompt-injection attempt asking the support agent to bypass verification and disclose addresses. The recorded tool result reports failed verification, and the agent refuses to disclose private information. The trace makes the behavior behind the score visible.

![Execution trace for a prompt-injection test, showing rubric scores, a refusal to disclose addresses, and a failed-verification tool result](docs/images/execution-trace.png)

### 7. Compare versions and decide what to improve next

After revising and evaluating an agent, select **Compare** from its version history. The first selected version becomes the reference; use **+** to add other versions. Compare average evaluation scores by test category, then expand a category to inspect adherence, consistency, and grounding. Arrows indicate increases or decreases relative to the reference.

In the example shown, the boundary-probe score rises from 28.3% to 91.7%, while policy bypass falls from 100% to 96.7%. Seeing both changes helps teams identify remaining weaknesses even as other results improve. Category scores average the three rubric dimensions equally across evaluated tests in that category; each version's results reflect its own generated suite.

![Evaluation comparison between Northstar Shop Support versions 1.0 and 1.1, with category scores, expanded rubric dimensions, and improvement or regression arrows](docs/images/evaluation-comparison.png)

## Built with

React, TypeScript, Vite, and Tailwind power the workspace. FastAPI, Pydantic, SQLAlchemy, and Alembic provide the API, validation, persistence, and migrations. SQLite keeps local setup lightweight; PostgreSQL can be configured through the database URL.

Explore the API with the [agent examples](examples/README.md), which include a one-command Task Manager evaluation and explain how to read and extend the code.

**Run locally:** [Backend setup](backend/README.md) · [Frontend setup](frontend/README.md)

## Git hooks

After installing the frontend and backend development dependencies, enable the
repository's hooks once per clone from the repository root:

```bash
git config core.hooksPath .githooks
```

The pre-commit hook runs `npm run check` in `frontend` and Ruff's lint and format
checks in `backend`. It checks the full working tree without changing files and
blocks the commit if any check fails. Ruff uses `backend/.venv/bin/python` when
available, otherwise `python3` (or `python`) from your environment.

To fix failures, run `npm run fix` in `frontend`, or `python -m ruff check . --fix`
and `python -m ruff format .` in `backend` with the backend environment activated.
Stage the fixes before committing again.
