import { type LlmProviderInfo, fetchLlmOnboarding } from "@/lib/api";
import { useStore } from "@/lib/store";
import { motion } from "framer-motion";
import { CheckCircle2, Cpu, RefreshCw, Settings as SettingsIcon, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface Onboarding {
  llm_required: boolean;
  llm_detected: boolean;
  recommended_provider: string;
  steps: string[];
}

export default function Settings() {
  const providers = useStore((s) => s.providers);
  const llmProvider = useStore((s) => s.llmProvider);
  const llmModel = useStore((s) => s.llmModel);
  const llmAvailable = useStore((s) => s.llmAvailable);
  const llmProbing = useStore((s) => s.llmProbing);
  const setLlmProvider = useStore((s) => s.setLlmProvider);
  const setLlmModel = useStore((s) => s.setLlmModel);
  const discoverLlm = useStore((s) => s.discoverLlm);

  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    discoverLlm();
    fetchLlmOnboarding()
      .then(setOnboarding)
      .catch(() => {});
  }, [discoverLlm]);

  const testProvider = useCallback(
    async (id: string) => {
      setTesting(id);
      await discoverLlm();
      setTesting(null);
    },
    [discoverLlm],
  );

  const models: string[] = (providers[llmProvider]?.models as string[]) || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="settings">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Settings</h2>
        <p className="text-sm text-zinc-300 mt-1">Local models and server configuration</p>
      </div>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="llm-onboarding">
        <div className="flex items-center gap-2 mb-3">
          <Cpu size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Local LLM</h3>
          <span
            className={`ml-auto text-sm font-medium ${llmAvailable ? "text-green-400" : llmProbing ? "text-amber-400" : "text-zinc-300"}`}
            data-testid="llm-status-text"
          >
            {llmProbing ? "Probing..." : llmAvailable ? "Detected" : "Not detected"}
          </span>
        </div>
        <p className="text-sm text-zinc-300">
          Chat, auto-fill, summaries, and the <span className="font-mono">pdf_do</span> agent need a local LLM. Everything else works
          without one.
        </p>
        {onboarding?.steps && (
          <ul className="mt-3 space-y-1 text-sm text-zinc-300 list-disc ml-5">
            {onboarding.steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(["ollama", "lmstudio"] as const).map((id) => {
          const p = providers[id] as LlmProviderInfo | undefined;
          const available = !!p?.available;
          return (
            <motion.div
              key={id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-5"
              data-testid={`llm-provider-card-${id}`}
            >
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-zinc-100">{p?.name || (id === "ollama" ? "Ollama" : "LM Studio")}</h4>
                {available ? <CheckCircle2 size={18} className="text-green-400" /> : <XCircle size={18} className="text-zinc-300" />}
              </div>
              <p className="text-sm text-zinc-300 mt-1 font-mono">
                {p?.base_url || (id === "ollama" ? "127.0.0.1:11434" : "127.0.0.1:1234")}
              </p>
              <p className="text-sm text-zinc-300 mt-2">{available ? `${p?.models?.length || 0} models available` : "Not running"}</p>
              <button
                type="button"
                onClick={() => testProvider(id)}
                disabled={testing === id}
                className="mt-3 flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-200 rounded-lg text-sm hover:bg-zinc-700 transition-colors disabled:opacity-50"
                data-testid={`llm-test-${id}`}
              >
                <RefreshCw size={14} className={testing === id ? "animate-spin" : ""} /> Test connection
              </button>
            </motion.div>
          );
        })}
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
        <h3 className="text-lg font-semibold text-zinc-100">Active model</h3>
        {llmAvailable ? (
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1 text-sm text-zinc-300">
              Provider
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
                data-testid="llm-provider-select"
              >
                {Object.entries(providers)
                  .filter(([, v]) => v.available)
                  .map(([id, v]) => (
                    <option key={id} value={id}>
                      {v.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm text-zinc-300">
              Model
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-amber-500 min-w-64"
                data-testid="llm-model-select"
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : (
          <p className="text-sm text-zinc-300" data-testid="llm-settings-empty">
            No local LLM running. Start Ollama or LM Studio and use “Test connection”.
          </p>
        )}
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <SettingsIcon size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Server</h3>
        </div>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
          <div className="flex justify-between border-b border-zinc-800 py-1.5">
            <dt className="text-zinc-300">Backend port</dt>
            <dd className="font-mono text-zinc-200">11131</dd>
          </div>
          <div className="flex justify-between border-b border-zinc-800 py-1.5">
            <dt className="text-zinc-300">Frontend port</dt>
            <dd className="font-mono text-zinc-200">11130</dd>
          </div>
          <div className="flex justify-between border-b border-zinc-800 py-1.5">
            <dt className="text-zinc-300">Transport</dt>
            <dd className="font-mono text-zinc-200">stdio + HTTP</dd>
          </div>
          <div className="flex justify-between border-b border-zinc-800 py-1.5">
            <dt className="text-zinc-300">RAG store</dt>
            <dd className="font-mono text-zinc-200">data/lancedb</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
