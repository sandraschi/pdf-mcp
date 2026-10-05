import { fetchFleetApps } from "@/lib/api";
import { motion } from "framer-motion";
import { Boxes, ExternalLink, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface AppEntry {
  name?: string;
  port?: number;
  frontend_port?: number;
  repo?: string;
  [k: string]: unknown;
}

export default function Apps() {
  const [apps, setApps] = useState<AppEntry[]>([]);
  const [registry, setRegistry] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await fetchFleetApps();
      setApps(d.apps || []);
      setRegistry(d.registry);
    } catch {
      setApps([]);
      setRegistry(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const known = registry ? apps : [];
  const experimental = registry ? [] : apps;

  const card = (a: AppEntry, i: number) => (
    <motion.div
      key={a.name || i}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 border border-zinc-800 rounded-xl p-5"
      data-testid="app-card"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-zinc-100 truncate">{a.name || "(unnamed)"}</h4>
        <Boxes size={16} className="text-amber-500 shrink-0" />
      </div>
      <p className="text-sm text-zinc-300 mt-1">
        {a.frontend_port || a.port ? (
          <a
            className="inline-flex items-center gap-1 text-amber-400 hover:text-amber-300 font-mono"
            href={`http://127.0.0.1:${a.frontend_port || a.port}`}
            target="_blank"
            rel="noreferrer"
          >
            :{a.frontend_port || a.port} <ExternalLink size={11} />
          </a>
        ) : (
          <span className="text-zinc-300">no port</span>
        )}
      </p>
      {a.repo ? <p className="text-sm text-zinc-300 mt-1 font-mono truncate">{String(a.repo)}</p> : null}
    </motion.div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="apps">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Apps Hub</h2>
          <p className="text-sm text-zinc-300 mt-1">Fleet webapps discovered from the registry</p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="p-2 rounded-lg text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          data-testid="apps-refresh"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {apps.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-300" data-testid="apps-empty">
          <Boxes size={48} className="mb-3 opacity-60" />
          <p className="text-sm">No apps discovered. Is the fleet registry present?</p>
        </div>
      ) : (
        <>
          <section>
            <h3 className="text-lg font-semibold text-zinc-100 mb-3">Registered</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="apps-registered">
              {known.map(card)}
            </div>
          </section>
          {experimental.length > 0 && (
            <section data-testid="apps-experimental">
              <h3 className="text-lg font-semibold text-zinc-100 mb-3">Experimental</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{experimental.map(card)}</div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
