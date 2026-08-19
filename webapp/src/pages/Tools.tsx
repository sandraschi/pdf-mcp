import { fetchTools } from "@/lib/api";
import { motion } from "framer-motion";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { useEffect, useState } from "react";

export default function Tools() {
  const [tools, setTools] = useState<Array<{ name: string; description: string; inputSchema: Record<string, unknown> }>>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchTools()
      .then(setTools)
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="tools">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Tools</h2>
        <p className="text-sm text-zinc-500 mt-1">{tools.length} tools available</p>
      </div>

      {tools.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-600">
          <Wrench size={48} className="mb-3 opacity-50" />
          <p className="text-sm">No tools discovered. Is the backend running?</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="tools-list">
          {tools.map((tool) => {
            const isExpanded = expanded === tool.name;
            const schema = tool.inputSchema;
            const properties = (schema?.properties as Record<string, { description?: string; type?: string }>) || {};
            const required = (schema?.required as string[]) || [];
            const opProp = properties?.operation as { enum?: string[] } | undefined;
            const subOps = opProp?.enum;

            return (
              <motion.div
                key={tool.name}
                data-testid="tool-item"
                className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <button
                  type="button"
                  onClick={() => setExpanded(isExpanded ? null : tool.name)}
                  className="w-full flex items-center justify-between px-5 py-4 hover:bg-zinc-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/10 rounded-lg">
                      <Wrench size={16} className="text-amber-500" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium text-zinc-100">{tool.name}</p>
                      <p className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{tool.description}</p>
                    </div>
                  </div>
                  {isExpanded ? <ChevronDown size={16} className="text-zinc-500" /> : <ChevronRight size={16} className="text-zinc-500" />}
                </button>

                {isExpanded && (
                  <div className="px-5 pb-4 space-y-3 border-t border-zinc-800 pt-3" data-testid="tool-details">
                    <p className="text-sm text-zinc-400">{tool.description}</p>

                    {subOps && subOps.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Sub-operations</p>
                        <div className="flex flex-wrap gap-2">
                          {subOps.map((op) => (
                            <span key={op} className="px-2.5 py-1 bg-zinc-800 rounded text-xs text-zinc-300">
                              {op}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(properties).length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Parameters</p>
                        <div className="space-y-1">
                          {Object.entries(properties).map(([key, val]) => (
                            <div key={key} className="flex items-start gap-2 text-xs">
                              <span className="font-mono text-amber-400/80 whitespace-nowrap">{key}</span>
                              <span className="text-zinc-500">{val?.type || "any"}</span>
                              {required.includes(key) && <span className="text-red-400">required</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
