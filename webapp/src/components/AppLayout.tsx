import { useBackendStatus } from "@/hooks/useBackendStatus";
import { useZoom } from "@/hooks/useZoom";
import { useStore } from "@/lib/store";
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppLayout({ children }: { children: ReactNode }) {
  const collapsed = useStore((s) => s.sidebarCollapsed);
  const setCollapsed = useStore((s) => s.setSidebarCollapsed);
  const healthCheck = useStore((s) => s.healthCheck);
  const discoverLlm = useStore((s) => s.discoverLlm);
  const loadCapabilities = useStore((s) => s.loadCapabilities);
  const navigate = useNavigate();
  const { zoom } = useZoom();
  useBackendStatus();

  // Global bootstrap: poll backend health, probe for a local LLM, and load the
  // capability introspection payload (WEBAPP_STANDARDS 1.4) on every route.
  useEffect(() => {
    healthCheck();
    discoverLlm();
    loadCapabilities();
  }, [healthCheck, discoverLlm, loadCapabilities]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey || e.altKey || e.metaKey) return;
      const key = e.key.toLowerCase();
      if (key === "l") {
        e.preventDefault();
        navigate("/logs");
      } else if (key === "h") {
        e.preventDefault();
        navigate("/help");
      } else if (key === "k") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pdf-search-focus"));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    <div id="app-root" className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar zoom={zoom} />
        <motion.main
          className="flex-1 overflow-y-auto p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
