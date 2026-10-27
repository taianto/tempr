import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AgentPage } from "./agent-page";
import { AgentsPage } from "./agents-page";
import { agentsApi, classificationsApi, versionsApi } from "./api";
import { ComparePage } from "./compare-page";
import { ClassificationPanel } from "./components/classification-panel";
import type { Agent, AgentVersion, Classification, ClassificationScores } from "./types";

vi.mock("./api", () => ({
  agentsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  versionsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn() },
  classificationsApi: { classify: vi.fn(), get: vi.fn() },
}));

const scoreKeys: (keyof ClassificationScores)[] = [
  "happy_path",
  "boundary_probe",
  "missing_information",
  "ambiguous_input",
  "prompt_injection",
  "policy_bypass",
  "sensitive_data_request",
  "hallucination_probe",
];
const scores: ClassificationScores = {
  happy_path: 0.5,
  boundary_probe: 0.5,
  missing_information: 0,
  ambiguous_input: 0,
  prompt_injection: 0,
  policy_bypass: 0,
  sensitive_data_request: 0,
  hallucination_probe: 0,
};
const emptyScores: ClassificationScores = Object.fromEntries(
  scoreKeys.map((key) => [key, 0.125]),
) as ClassificationScores;
const classification: Classification = {
  id: "cls-1",
  scores,
  classifier_model: "test",
  created_at: "2026-10-15T10:00:00Z",
  updated_at: "2026-10-15T10:00:00Z",
};
const generated: Classification = { ...classification, id: "cls-new", scores: emptyScores };
const schema = {
  description: "A test agent",
  prompt: { system: "Be helpful", developer: null },
  model: null,
  tools: [],
  metadata: {},
};
const v1: AgentVersion = {
  id: "agv-1",
  agent_id: "agt-1",
  version: "1.0",
  created_at: "2026-10-14T10:00:00Z",
  classification_id: "cls-1",
  schema,
  classification,
};
const v2: AgentVersion = {
  id: "agv-2",
  agent_id: "agt-1",
  version: "2.0-beta",
  created_at: "2026-10-15T10:00:00Z",
  classification_id: null,
  schema: { ...schema, prompt: { system: "Be more helpful", developer: null } },
  classification: null,
};
const agent: Agent = {
  id: "agt-1",
  name: "Support agent",
  created_at: "2026-10-10T10:00:00Z",
  updated_at: "2026-10-15T10:00:00Z",
  latest_version: v2,
};
let versionStore: Record<string, AgentVersion>;

function LocationText() {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname}
      {location.search}
    </output>
  );
}
function renderRoute(initialEntry: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <LocationText />
        <Routes>
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:agentId" element={<AgentPage />} />
          <Route path="/agents/:agentId/compare" element={<ComparePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  versionStore = { "agv-1": { ...v1 }, "agv-2": { ...v2 } };
  vi.mocked(agentsApi.list).mockResolvedValue({
    items: [
      {
        id: agent.id,
        name: agent.name,
        created_at: agent.created_at,
        updated_at: agent.updated_at,
        latest_version: {
          id: v2.id,
          version: v2.version,
          created_at: v2.created_at,
          classification_id: null,
        },
      },
    ],
    total: 1,
  });
  vi.mocked(agentsApi.get).mockImplementation(async () => ({
    ...agent,
    latest_version: { ...versionStore["agv-2"] },
  }));
  vi.mocked(versionsApi.list).mockResolvedValue({ items: [v2, v1], total: 2 });
  vi.mocked(versionsApi.get).mockImplementation(async (versionId) => {
    const value = versionStore[versionId];
    if (!value) throw Object.assign(new Error("Version not found"), { status: 404 });
    return { ...value };
  });
  vi.mocked(classificationsApi.classify).mockImplementation(async (versionId) => {
    versionStore[versionId] = {
      ...versionStore[versionId],
      classification: generated,
      classification_id: generated.id,
    };
    return generated;
  });
});

describe("versioned agent workspace", () => {
  it("opens an agent from the list and shows its latest version and allocation prompt", async () => {
    const user = userEvent.setup();
    renderRoute("/agents");
    await user.click(await screen.findByRole("link", { name: /open agent/i }));
    expect(await screen.findByRole("heading", { name: "Support agent" })).toBeInTheDocument();
    expect(screen.getByText("2.0-beta")).toBeInTheDocument();
    expect(
      screen.getByText("Classify your agent to plan its first test suite"),
    ).toBeInTheDocument();
  });

  it("sorts category bars with stable ties, generates the latest version, and retains scores after a failed refresh", async () => {
    const user = userEvent.setup();
    renderRoute("/agents/agt-1");
    await user.click(await screen.findByRole("button", { name: "Generate classification" }));
    await waitFor(() => expect(classificationsApi.classify).toHaveBeenCalledTimes(1));
    expect(await screen.findAllByText("13%")).toHaveLength(8);

    vi.mocked(classificationsApi.classify).mockRejectedValueOnce(new Error("Provider unavailable"));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    await user.click(await screen.findByRole("button", { name: "Regenerate" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Provider unavailable"),
    );
    const chart = screen.getByRole("heading", { name: "Version 2.0-beta" }).closest("section");
    if (!chart) throw new Error("Could not find the classification chart.");
    expect(chart.querySelector('[data-category="happy_path"]')?.textContent).toContain("13%");
    expect(confirm).toHaveBeenCalled();
    expect(
      [...chart.querySelectorAll("[data-category]")]
        .map((row) => row.getAttribute("data-category"))
        .slice(0, 3),
    ).toEqual(["happy_path", "boundary_probe", "missing_information"]);
    expect(
      chart.querySelector('[data-category="happy_path"] > div:nth-child(2) > div > div'),
    ).toHaveStyle({ width: "12.5%" });
    confirm.mockRestore();
  });

  it("renders zero weight categories with zero width and labels independent of color", () => {
    const client = new QueryClient();
    const { container } = render(
      <QueryClientProvider client={client}>
        <ClassificationPanel version={v1} />
      </QueryClientProvider>,
    );
    expect(
      container.querySelector(
        '[data-category="missing_information"] > div:nth-child(2) > div > div',
      ),
    ).toHaveStyle({ width: "0%" });
    expect(screen.getByText("Missing information")).toBeInTheDocument();
    client.clear();
  });

  it("creates a new immutable version from the version-specific JSON contract", async () => {
    const user = userEvent.setup();
    vi.mocked(versionsApi.create).mockResolvedValue({
      ...v2,
      id: "agv-3",
      version: "release-candidate",
      classification: null,
      classification_id: null,
    });
    renderRoute("/agents/agt-1");
    await screen.findByRole("heading", { name: "Support agent" });
    await user.click(screen.getAllByRole("button", { name: "New version" })[0]);
    const input = screen.getByLabelText("Version JSON");
    fireEvent.change(input, {
      target: {
        value: JSON.stringify({
          version: "release-candidate",
          schema: { prompt: { system: "Ship it" } },
        }),
      },
    });
    await user.click(screen.getByRole("button", { name: "Create version" }));
    await waitFor(() =>
      expect(versionsApi.create).toHaveBeenCalledWith("agt-1", {
        version: "release-candidate",
        schema: { prompt: { system: "Ship it" } },
      }),
    );
  });

  it("renames an agent through the name-only update endpoint", async () => {
    const user = userEvent.setup();
    vi.mocked(agentsApi.update).mockResolvedValue(agent);
    renderRoute("/agents/agt-1");
    await screen.findByRole("heading", { name: "Support agent" });
    await user.click(screen.getByRole("button", { name: "Rename" }));
    await user.clear(screen.getByLabelText("Agent name"));
    await user.type(screen.getByLabelText("Agent name"), "Refund assistant");
    await user.click(screen.getByRole("button", { name: "Save name" }));
    await waitFor(() =>
      expect(agentsApi.update).toHaveBeenCalledWith("agt-1", { name: "Refund assistant" }),
    );
  });

  it("removes the agent after confirmation and returns to the list", async () => {
    const user = userEvent.setup();
    vi.mocked(agentsApi.delete).mockResolvedValue(undefined);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderRoute("/agents/agt-1");
    await screen.findByRole("heading", { name: "Support agent" });
    await user.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(agentsApi.delete).toHaveBeenCalledWith("agt-1"));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/agents"));
    confirm.mockRestore();
  });

  it("shows a useful state when an agent is missing", async () => {
    vi.mocked(agentsApi.get).mockRejectedValue(
      Object.assign(new Error("Agent not found"), { status: 404 }),
    );
    renderRoute("/agents/missing");
    expect(
      await screen.findByRole("heading", { name: "Unable to load agent" }),
    ).toBeInTheDocument();
  });

  it("restores selected columns from the URL, adds a version after its column, and generates it only on request", async () => {
    const user = userEvent.setup();
    renderRoute("/agents/agt-1/compare?versions=agv-1");
    expect(await screen.findByRole("columnheader", { name: /version 1\.0/i })).toBeInTheDocument();
    const menus = screen.getAllByLabelText("Add a version to comparison");
    menus[0].focus();
    await user.keyboard("{Enter}");
    await user.click(screen.getByRole("menuitem", { name: "Version 2.0-beta" }));
    expect(
      await screen.findByRole("columnheader", { name: /version 2\.0-beta/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("versions=agv-1%2Cagv-2");
    const duplicateMenu = screen.getAllByLabelText("Add a version to comparison")[0];
    await user.click(duplicateMenu);
    expect(screen.queryByRole("menuitem", { name: "Version 1.0" })).not.toBeInTheDocument();
    await user.keyboard("{Escape}");

    const classifyButton = screen.getByRole("button", {
      name: /generate classification for this version/i,
    });
    await user.click(classifyButton);
    await waitFor(() => expect(classificationsApi.classify).toHaveBeenCalledWith("agv-2", false));
    expect(await screen.findAllByText("13%")).toHaveLength(8);
  });

  it("defaults a comparison with no version parameter to the latest version", async () => {
    renderRoute("/agents/agt-1/compare");
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("versions=agv-2"));
    expect(
      await screen.findByRole("columnheader", { name: /version 2\.0-beta/i }),
    ).toBeInTheDocument();
  });

  it("marks a version from another agent unavailable and hides classification actions", async () => {
    vi.mocked(versionsApi.get).mockResolvedValue({ ...v1, agent_id: "agt-other" });
    renderRoute("/agents/agt-1/compare?versions=agv-1");

    expect(
      await screen.findByRole("columnheader", { name: /unavailable version/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /generate classification for this version/i }),
    ).not.toBeInTheDocument();
  });

  it("submits agent creation with the nested initial version contract", async () => {
    const user = userEvent.setup();
    vi.mocked(agentsApi.create).mockResolvedValue(agent);
    renderRoute("/agents");
    await user.click(await screen.findByRole("button", { name: "New agent" }));
    const input = screen.getByLabelText("Agent JSON");
    await user.clear(input);
    fireEvent.change(input, {
      target: {
        value: JSON.stringify({
          name: "Support agent",
          initial_version: { version: "1.0", schema: { prompt: { system: "Be helpful" } } },
        }),
      },
    });
    await user.click(screen.getByRole("button", { name: "Create agent" }));
    await waitFor(() =>
      expect(agentsApi.create).toHaveBeenCalledWith({
        name: "Support agent",
        initial_version: { version: "1.0", schema: { prompt: { system: "Be helpful" } } },
      }),
    );
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/agents/agt-1"));
  });
});
