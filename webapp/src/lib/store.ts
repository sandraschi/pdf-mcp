import { create } from "zustand";
import { type LlmProviderInfo, fetchHealth, fetchLlmDiscover } from "./api";

const LLM_PROVIDER_KEY = "llm_provider";
const LLM_MODEL_KEY = "llm_model";

interface AppState {
  backendOk: boolean | null;
  backendStatus: "connecting" | "connected" | "offline";
  toolCount: number;
  version: string;
  uptime: number;
  sidebarCollapsed: boolean;
  pageTitle: string;
  setBackendOk: (ok: boolean | null) => void;
  setBackendStatus: (s: "connecting" | "connected" | "offline") => void;
  setToolCount: (n: number) => void;
  setVersion: (v: string) => void;
  setUptime: (n: number) => void;
  setSidebarCollapsed: (c: boolean) => void;
  setPageTitle: (t: string) => void;
  healthCheck: () => Promise<void>;

  providers: Record<string, LlmProviderInfo>;
  llmAvailable: boolean;
  llmProbing: boolean;
  llmProvider: string;
  llmModel: string;
  setLlmProvider: (p: string) => void;
  setLlmModel: (m: string) => void;
  discoverLlm: () => Promise<void>;
}

export const useStore = create<AppState>((set) => ({
  backendOk: null,
  backendStatus: "connecting",
  toolCount: 0,
  version: "",
  uptime: 0,
  sidebarCollapsed: false,
  pageTitle: "Dashboard",
  setBackendOk: (ok) => set({ backendOk: ok }),
  setBackendStatus: (s) => set({ backendStatus: s }),
  setToolCount: (n) => set({ toolCount: n }),
  setVersion: (v) => set({ version: v }),
  setUptime: (n) => set({ uptime: n }),
  setSidebarCollapsed: (c) => set({ sidebarCollapsed: c }),
  setPageTitle: (t) => set({ pageTitle: t }),
  healthCheck: async () => {
    try {
      const h = await fetchHealth();
      set({ backendOk: true, backendStatus: "connected", toolCount: h.tool_count, version: h.version, uptime: h.uptime_seconds });
    } catch {
      set({ backendOk: false, backendStatus: "offline" });
    }
  },

  providers: {},
  llmAvailable: false,
  llmProbing: false,
  llmProvider: localStorage.getItem(LLM_PROVIDER_KEY) || "",
  llmModel: localStorage.getItem(LLM_MODEL_KEY) || "",
  setLlmProvider: (p) => {
    localStorage.setItem(LLM_PROVIDER_KEY, p);
    const model = localStorage.getItem(LLM_MODEL_KEY) || "";
    set({ llmProvider: p, llmModel: model, llmAvailable: true });
  },
  setLlmModel: (m) => {
    localStorage.setItem(LLM_MODEL_KEY, m);
    set({ llmModel: m });
  },
  discoverLlm: async () => {
    set({ llmProbing: true });
    try {
      const d = await fetchLlmDiscover();
      const available = Object.values(d.providers).some((p) => p.available);
      const saved = localStorage.getItem(LLM_PROVIDER_KEY) || "";
      const provider = saved && d.providers[saved]?.available ? saved : d.default_provider || "";
      const providerModels = provider ? d.providers[provider].models : [];
      const savedModel = localStorage.getItem(LLM_MODEL_KEY) || "";
      const model = providerModels.includes(savedModel) ? savedModel : providerModels[0] || "";
      if (model) localStorage.setItem(LLM_MODEL_KEY, model);
      set({ providers: d.providers, llmAvailable: available, llmProvider: provider, llmModel: model, llmProbing: false });
    } catch {
      set({ llmProbing: false });
    }
  },
}));
