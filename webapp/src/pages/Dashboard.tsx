import { motion } from "framer-motion";
import { Server, Hash, Clock, Activity, FileText, Workflow, MessageSquare } from "lucide-react";
import { useStore } from "@/lib/store";
import BackendDot from "@/components/BackendDot";

function formatUptime(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${h}h ${m}m ${sec}s`;
}

function KpiCard({ label, icon: Icon, value, testid }: { label: string; icon: typeof Server; value: string | null; testid: string }) {
  return (
    <motion.div
      className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-center gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      data-testid={testid}
    >
      <div className="p-3 bg-amber-500/10 rounded-lg">
        <Icon size={24} className="text-amber-500" />
      </div>
      <div>
        <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
        <p className="text-xl font-semibold text-zinc-100 mt-1">
          {value ?? <span className="inline-block w-16 h-5 bg-zinc-800 rounded animate-pulse" />}
        </p>
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  const version = useStore((s) => s.version);
  const toolCount = useStore((s) => s.toolCount);
  const uptime = useStore((s) => s.uptime);
  const backendOk = useStore((s) => s.backendOk);

  return (
    <div className="max-w-5xl mx-auto space-y-8" data-testid="dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Dashboard</h2>
          <p className="text-sm text-zinc-500 mt-1">Overview of the pdf-mcp server</p>
        </div>
        <BackendDot />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Server" icon={Server} value="pdf-mcp" testid="kpi-server" />
        <KpiCard label="Version" icon={Hash} value={version || null} testid="kpi-version" />
        <KpiCard label="Tools" icon={Activity} value={toolCount > 0 ? String(toolCount) : null} testid="kpi-tools" />
        <KpiCard label="Uptime" icon={Clock} value={uptime > 0 ? formatUptime(uptime) : null} testid="kpi-uptime" />
      </div>

      {backendOk === false && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <p className="text-red-400 font-medium">Backend is offline</p>
          <p className="text-zinc-500 text-sm mt-1">Start the backend server to access all features</p>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-zinc-100 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <a
            href="/workbench"
            className="flex items-center gap-3 px-4 py-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors text-zinc-300 hover:text-zinc-100"
          >
            <FileText size={18} className="text-amber-500" />
            <span className="text-sm font-medium">Open Workbench</span>
          </a>
          <a
            href="/pipeline"
            className="flex items-center gap-3 px-4 py-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors text-zinc-300 hover:text-zinc-100"
          >
            <Workflow size={18} className="text-amber-500" />
            <span className="text-sm font-medium">Batch Pipeline</span>
          </a>
          <a
            href="/chat"
            className="flex items-center gap-3 px-4 py-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors text-zinc-300 hover:text-zinc-100"
          >
            <MessageSquare size={18} className="text-amber-500" />
            <span className="text-sm font-medium">Ask the AI</span>
          </a>
        </div>
      </div>
    </div>
  );
}

