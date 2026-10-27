import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsApi, classificationsApi, testSuitesApi, versionsApi } from "../api";
import type {
  Agent,
  AgentCreateInput,
  AgentUpdateInput,
  AgentVersion,
  Classification,
  TestSuite,
  TestSuiteGeneration,
  VersionCreateInput,
} from "../types";

export const agentKeys = {
  all: ["agents"] as const,
  detail: (id: string) => ["agents", id] as const,
  versions: (id: string) => ["agents", id, "versions"] as const,
  version: (versionId: string) => ["versions", versionId] as const,
  testSuite: (versionId: string) => ["versions", versionId, "test-suite"] as const,
  classifications: ["classifications"] as const,
};

export function useAgents() {
  return useQuery({ queryKey: agentKeys.all, queryFn: ({ signal }) => agentsApi.list(signal) });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: ({ signal }) => agentsApi.get(id, signal),
    enabled: Boolean(id),
  });
}

export function useVersions(id: string) {
  return useQuery({
    queryKey: agentKeys.versions(id),
    queryFn: ({ signal }) => versionsApi.list(id, signal),
    enabled: Boolean(id),
  });
}

export function useVersion(versionId: string) {
  return useQuery({
    queryKey: agentKeys.version(versionId),
    queryFn: ({ signal }) => versionsApi.get(versionId, signal),
    enabled: Boolean(versionId),
    retry: (count, error) =>
      !(error instanceof Error && "status" in error && error.status === 404) && count < 1,
  });
}

export function useTestSuite(versionId: string) {
  return useQuery({
    queryKey: agentKeys.testSuite(versionId),
    queryFn: ({ signal }) => testSuitesApi.get(versionId, signal),
    enabled: Boolean(versionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 2_000 : false;
    },
  });
}

export function useGenerateTestSuite(versionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationKey: ["generate-test-suite", versionId],
    mutationFn: (totalCount: number) => testSuitesApi.generate(versionId, totalCount),
    onSuccess: async (generation: TestSuiteGeneration) => {
      const currentSuite: TestSuite = {
        ...generation,
        items: [],
        generated_at: null,
      };
      client.setQueryData<TestSuite | null>(agentKeys.testSuite(versionId), currentSuite);
      await client.invalidateQueries({ queryKey: agentKeys.testSuite(versionId) });
    },
  });
}

export function useCreateAgent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (agent: AgentCreateInput) => agentsApi.create(agent),
    onSuccess: async (agent) => {
      client.setQueryData(agentKeys.detail(agent.id), agent);
      await client.invalidateQueries({ queryKey: agentKeys.all });
    },
  });
}

export function useUpdateAgent(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (agent: AgentUpdateInput) => agentsApi.update(id, agent),
    onSuccess: async (agent) => {
      client.setQueryData<Agent>(agentKeys.detail(id), agent);
      await client.invalidateQueries({ queryKey: agentKeys.all });
    },
  });
}

export function useCreateVersion(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (version: VersionCreateInput) => versionsApi.create(id, version),
    onSuccess: async (version) => {
      client.setQueryData(agentKeys.version(version.id), version);
      await Promise.all([
        client.invalidateQueries({ queryKey: agentKeys.detail(id) }),
        client.invalidateQueries({ queryKey: agentKeys.versions(id) }),
        client.invalidateQueries({ queryKey: agentKeys.all }),
      ]);
    },
  });
}

export function useClassify(versionId: string, refresh = false) {
  const client = useQueryClient();
  return useMutation({
    mutationKey: ["classify", versionId],
    mutationFn: () => classificationsApi.classify(versionId, refresh),
    onSuccess: async (classification: Classification) => {
      const version = client.getQueryData<AgentVersion>(agentKeys.version(versionId));
      client.setQueryData<AgentVersion>(agentKeys.version(versionId), (previous) =>
        previous ? { ...previous, classification, classification_id: classification.id } : previous,
      );
      if (version) {
        client.setQueryData<Agent>(agentKeys.detail(version.agent_id), (previous) =>
          previous?.latest_version.id === versionId
            ? {
                ...previous,
                latest_version: {
                  ...previous.latest_version,
                  classification,
                  classification_id: classification.id,
                },
              }
            : previous,
        );
      }
      await Promise.all([
        client.invalidateQueries({ queryKey: agentKeys.version(versionId) }),
        client.invalidateQueries({ queryKey: agentKeys.classifications }),
        client.invalidateQueries({ queryKey: agentKeys.all }),
      ]);
    },
  });
}

export function useDeleteAgent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.delete(id),
    onSuccess: async (_, id) => {
      const detail = client.getQueryData<Agent>(agentKeys.detail(id));
      const cachedVersions = client.getQueryData<{ items: AgentVersion[] }>(agentKeys.versions(id));
      client.removeQueries({ queryKey: agentKeys.detail(id) });
      client.removeQueries({ queryKey: agentKeys.versions(id) });
      const versionIds = new Set([
        ...(cachedVersions?.items ?? []).map((version) => version.id),
        ...(detail ? [detail.latest_version.id] : []),
      ]);
      for (const versionId of versionIds) {
        client.removeQueries({ queryKey: agentKeys.version(versionId) });
        client.removeQueries({ queryKey: agentKeys.testSuite(versionId) });
      }
      await client.invalidateQueries({ queryKey: agentKeys.all });
    },
  });
}
