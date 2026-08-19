import BackendDot from "@/components/BackendDot";
import { fetchStats } from "@/lib/api";
import { useStore } from "@/lib/store";
import { motion } from "framer-motion";
import { Activity, BarChart3, Clock, Cpu, FileText, Hash, MessageSquare, Server, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

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
  const llmAvailable = useStore((s) => s.llmAvailable);
  const llmProbing = useStore((s) => s.llmProbing);
  const [stats, setStats] = useState<{
    operations: Array<{ operation: string; count: number; avg_ms: number }>;
    total_jobs: number;
    total_files: number;
  } | null>(null);

  useEffect(() => {
    if (backendOk !== true) return;
    fetchStats()
      .then(setStats)
      .catch(() => {});
  }, [backendOk]);

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
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center" data-testid="backend-offline-banner">
          <p className="text-red-400 font-medium">Backend is offline</p>
          <p className="text-zinc-500 text-sm mt-1">Start the backend server to access all features</p>
        </div>
      )}

      {backendOk === true && !llmProbing && !llmAvailable && (
        <div
          className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6 flex items-start gap-4"
          data-testid="llm-opportunity-banner"
        >
          <Cpu size={20} className="text-amber-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-amber-400 font-medium">No local LLM detected</p>
            <p className="text-zinc-400 text-sm mt-1">
              Start <span className="font-mono">ollama serve</span> or LM Studio to enable AI chat with RAG context. The PDF tooling works
              without it.
            </p>
            <a href="/chat" className="inline-block mt-3 text-sm text-amber-400 hover:text-amber-300 underline">
              Open Chat to set up a model
            </a>
          </div>
        </div>
      )}

      {stats && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="stats-panel">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-amber-500" />
            <h3 className="text-lg font-semibold text-zinc-100">Usage</h3>
            <span className="text-xs text-zinc-500 ml-auto">
              {stats.total_jobs} jobs · {stats.total_files} files
            </span>
          </div>
          {stats.operations.length === 0 ? (
            <p className="text-sm text-zinc-500">No operations run yet in this session.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider">
                  <th className="text-left py-2 font-medium">Operation</th>
                  <th className="text-right py-2 font-medium">Count</th>
                  <th className="text-right py-2 font-medium">Avg (ms)</th>
                </tr>
              </thead>
              <tbody>
                {stats.operations.slice(0, 8).map((op) => (
                  <tr key={op.operation} className="border-b border-zinc-800/40">
                    <td className="py-2 text-zinc-300">{op.operation}</td>
                    <td className="py-2 text-right text-zinc-300">{op.count}</td>
                    <td className="py-2 text-right text-zinc-500">{Math.round(op.avg_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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
