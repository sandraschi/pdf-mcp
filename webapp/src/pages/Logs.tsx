import { fetchLogs } from "@/lib/api";
import { motion } from "framer-motion";
import { RefreshCw, Search, Terminal } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const levels = ["all", "info", "warn", "error", "debug"];

export default function Logs() {
  const [logs, setLogs] = useState<Array<{ timestamp: string; level: string; source: string; message: string }>>([]);
  const [level, setLevel] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const l = await fetchLogs({ level: level === "all" ? undefined : level, search: search || undefined, limit: 200 });
      setLogs(l);
    } catch {
      /* backend may not be ready */
    }
    setLoading(false);
  }, [level, search]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  const levelColor = (lvl: string) => {
    switch (lvl) {
      case "error":
        return "text-red-400";
      case "warn":
        return "text-amber-400";
      case "info":
        return "text-blue-400";
      case "debug":
        return "text-zinc-500";
      default:
        return "text-zinc-400";
    }
  };

  return (
    <div className="h-full flex flex-col" data-testid="logs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Logs</h2>
          <p className="text-sm text-zinc-500 mt-1">Server logs and events</p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          data-testid="logs-refresh"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search logs..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-amber-500"
            data-testid="logs-search"
          />
        </div>
        <div className="flex gap-1">
          {levels.map((l) => (
            <button
              type="button"
              key={l}
              onClick={() => setLevel(l)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                level === l ? "bg-amber-500 text-black" : "bg-zinc-800 text-zinc-400 hover:text-zinc-100"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="grid grid-cols-[140px_70px_1fr] gap-0 text-xs font-medium text-zinc-500 uppercase tracking-wider px-4 py-3 border-b border-zinc-800">
          <span>Timestamp</span>
          <span>Level</span>
          <span>Message</span>
        </div>
        <div className="overflow-y-auto h-full max-h-[calc(100vh-280px)]">
          {logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-600">
              <Terminal size={36} className="mb-2 opacity-50" />
              <p className="text-sm">No logs yet</p>
            </div>
          ) : (
            logs.map((log, i) => (
              <motion.div
                key={`${log.timestamp}-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-[140px_70px_1fr] gap-0 px-4 py-2 text-xs border-b border-zinc-800/30 hover:bg-zinc-800/30 transition-colors font-mono"
              >
                <span className="text-zinc-600">{log.timestamp}</span>
                <span className={levelColor(log.level)}>{log.level}</span>
                <div className="flex gap-2">
                  {log.source && <span className="text-zinc-600 shrink-0">[{log.source}]</span>}
                  <span className="text-zinc-400 truncate">{log.message}</span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
