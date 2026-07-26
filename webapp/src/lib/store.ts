import { create } from "zustand";
import { fetchHealth } from "./api";

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
}));
