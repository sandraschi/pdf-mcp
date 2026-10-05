import { fetchJobs, fetchWatchStatus } from "@/lib/api";
import { motion } from "framer-motion";
import { FolderInput, Inbox as InboxIcon, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

export default function Inbox() {
  const [jobs, setJobs] = useState<Array<{ job_id: string; operation: string; status: string; created: string }>>([]);
  const [watch, setWatch] = useState<{ watching: boolean; processed: Array<{ file: string; job_id: string; at: string }> } | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setJobs(await fetchJobs());
    } catch {
      /* backend may not be ready */
    }
    try {
      setWatch(await fetchWatchStatus());
    } catch {
      setWatch(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  const statusColor = (s: string) =>
    s === "completed" ? "text-green-400" : s === "running" ? "text-amber-400" : s === "failed" ? "text-red-400" : "text-zinc-300";

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="inbox">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Inbox</h2>
          <p className="text-sm text-zinc-300 mt-1">Watch-folder activity and recent jobs</p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="p-2 rounded-lg text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          data-testid="inbox-refresh"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="inbox-watch">
        <div className="flex items-center gap-2 mb-2">
          <FolderInput size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Watch folder</h3>
          <span className={`ml-auto text-sm ${watch?.watching ? "text-green-400" : "text-zinc-300"}`} data-testid="inbox-watch-status">
            {watch?.watching ? "Watching data/watch/" : "Idle"}
          </span>
        </div>
        <p className="text-sm text-zinc-300">
          Drop a PDF into <span className="font-mono">data/watch/</span> and the <span className="font-mono">ingest</span> recipe runs
          automatically (analyze → index → brief).
        </p>
        {watch && watch.processed.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm" data-testid="inbox-watch-processed">
            {watch.processed
              .slice(-5)
              .reverse()
              .map((p) => (
                <li key={`${p.job_id}-${p.at}`} className="flex justify-between border-b border-zinc-800 py-1.5">
                  <span className="text-zinc-200 truncate">{p.file}</span>
                  <span className="font-mono text-zinc-300 text-sm">{p.job_id}</span>
                </li>
              ))}
          </ul>
        )}
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden" data-testid="inbox-jobs">
        <div className="px-5 py-3 border-b border-zinc-800 flex items-center gap-2">
          <InboxIcon size={16} className="text-amber-500" />
          <h3 className="text-sm font-semibold text-zinc-100">Recent jobs</h3>
        </div>
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-zinc-300" data-testid="inbox-empty">
            <InboxIcon size={36} className="mb-2 opacity-60" />
            <p className="text-sm">Nothing yet. Upload a PDF in the Workbench or Pipeline.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-300 text-sm uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Job</th>
                <th className="text-left px-5 py-3 font-medium">Operation</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-left px-5 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 20).map((j) => (
                <motion.tr key={j.job_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border-b border-zinc-800/50">
                  <td className="px-5 py-3 font-mono text-sm text-zinc-300">{j.job_id}</td>
                  <td className="px-5 py-3 text-zinc-300">{j.operation}</td>
                  <td className={`px-5 py-3 font-medium ${statusColor(j.status)}`}>{j.status}</td>
                  <td className="px-5 py-3 text-zinc-300 text-sm">{j.created}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
