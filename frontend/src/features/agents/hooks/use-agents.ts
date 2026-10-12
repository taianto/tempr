import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsApi } from "../api";
import type { Agent, AgentCreateInput, AgentUpdateInput } from "../types";

export function useAgents() {
  return useQuery({ queryKey: ["agents"], queryFn: ({ signal }) => agentsApi.list(signal) });
}

export function useAgent(id: string, open: boolean) {
  return useQuery({ queryKey: ["agents", id], queryFn: ({ signal }) => agentsApi.get(id, signal), enabled: open && Boolean(id) });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agent: AgentCreateInput) => agentsApi.create(agent),
    onSuccess: async (agent) => {
      queryClient.setQueryData(["agents", agent.id], agent);
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useUpdateAgent(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agent: AgentUpdateInput) => agentsApi.update(id, agent),
    onSuccess: async (agent) => {
      queryClient.setQueryData<Agent>(["agents", id], agent);
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.delete(id),
    onSuccess: async (_, id) => {
      queryClient.removeQueries({ queryKey: ["agents", id] });
      await queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}
