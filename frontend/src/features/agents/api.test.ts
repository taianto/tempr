import { afterEach, describe, expect, it, vi } from "vitest";
import { classificationsApi, versionsApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("resource API clients", () => {
  it("uses flat version routes and includes the owning agent on creation", async () => {
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetch);

    await versionsApi.list("agt/one");
    await versionsApi.get("agv one");
    await versionsApi.create("agt-1", {
      version: "2.0",
      schema: { prompt: { system: "test" } },
    });

    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/versions?agent_id=agt%2Fone",
      "/api/v1/versions/agv%20one",
      "/api/v1/versions",
    ]);
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({
      agent_id: "agt-1",
      version: "2.0",
      schema: { prompt: { system: "test" } },
    });
  });

  it("classifies by version ID and retrieves by classification ID", async () => {
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetch);

    await classificationsApi.classify("agv-1", true);
    await classificationsApi.get("cls-1");

    expect(fetch.mock.calls[0][0]).toBe("/api/v1/classifications?refresh=true");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ version_id: "agv-1" });
    expect(fetch.mock.calls[1][0]).toBe("/api/v1/classifications/cls-1");
  });
});
