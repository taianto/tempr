import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AgentsPage } from "@/features/agents/agents-page";
import { AgentPage } from "@/features/agents/agent-page";
import { ComparePage } from "@/features/agents/compare-page";

export default function App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<Navigate to="/agents" replace />} />
    <Route path="/agents" element={<AgentsPage />} />
    <Route path="/agents/:agentId" element={<AgentPage />} />
    <Route path="/agents/:agentId/compare" element={<ComparePage />} />
    <Route path="*" element={<Navigate to="/agents" replace />} />
  </Routes></BrowserRouter>;
}
