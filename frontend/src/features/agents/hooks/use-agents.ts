import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsApi } from "../api";
import type {
  Agent,
  AgentCreateInput,
  AgentUpdateInput,
  AgentVersion,
  Classification,
  VersionCreateInput,
} from "../types";

export const agentKeys = {
  all: ["agents"] as const,
  detail: (id: string) => ["agents", id] as const,
  versions: (id: string) => ["agents", id, "versions"] as const,
  version: (id: string, versionId: string) => ["agents", id, "versions", versionId] as const,
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
    queryFn: ({ signal }) => agentsApi.listVersions(id, signal),
    enabled: Boolean(id),
  });
}

export function useVersion(id: string, versionId: string) {
  return useQuery({
    queryKey: agentKeys.version(id, versionId),
    queryFn: ({ signal }) => agentsApi.getVersion(id, versionId, signal),
    enabled: Boolean(id && versionId),
    retry: (count, error) =>
      !(error instanceof Error && "status" in error && error.status === 404) && count < 1,
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
    mutationFn: (version: VersionCreateInput) => agentsApi.createVersion(id, version),
    onSuccess: async (version) => {
      client.setQueryData(agentKeys.version(id, version.id), version);
      await Promise.all([
        client.invalidateQueries({ queryKey: agentKeys.detail(id) }),
        client.invalidateQueries({ queryKey: agentKeys.versions(id) }),
        client.invalidateQueries({ queryKey: agentKeys.all }),
      ]);
    },
  });
}

export function useClassify(id: string, versionId: string, refresh = false) {
  const client = useQueryClient();
  return useMutation({
    mutationKey: ["classify", id, versionId],
    mutationFn: () => agentsApi.classify(id, versionId, refresh),
    onSuccess: async (classification: Classification) => {
      client.setQueryData<AgentVersion>(agentKeys.version(id, versionId), (previous) =>
        previous ? { ...previous, classification, classification_id: classification.id } : previous,
      );
      client.setQueryData<Agent>(agentKeys.detail(id), (previous) =>
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
      await Promise.all([
        client.invalidateQueries({ queryKey: agentKeys.version(id, versionId) }),
        client.invalidateQueries({ queryKey: agentKeys.detail(id) }),
        client.invalidateQueries({ queryKey: agentKeys.versions(id) }),
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
      client.removeQueries({ queryKey: agentKeys.detail(id) });
      client.removeQueries({ queryKey: agentKeys.versions(id) });
      await client.invalidateQueries({ queryKey: agentKeys.all });
    },
  });
}
