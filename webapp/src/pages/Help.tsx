import { fetchTools } from "@/lib/api";
import { BookOpen, ExternalLink, FileCode, Keyboard, LifeBuoy, Terminal } from "lucide-react";
import { useEffect, useState } from "react";

const shortcuts = [
  { keys: "Ctrl + Scroll", action: "Zoom in/out (persisted)" },
  { keys: "Ctrl + 0", action: "Reset zoom to 100%" },
  { keys: "Ctrl + L", action: "Open Logs" },
  { keys: "Ctrl + H", action: "Open Tools" },
  { keys: "Ctrl + K", action: "Focus the Chat PDF search" },
];

const docs = [
  { label: "Configuration", href: "/docs/CONFIGURATION.md" },
  { label: "Tools & endpoints", href: "/docs/TOOLS.md" },
  { label: "Development", href: "/docs/DEVELOPMENT.md" },
  { label: "Onboarding", href: "/docs/ONBOARDING.md" },
  { label: "Troubleshooting", href: "/docs/TROUBLESHOOTING.md" },
];

export default function Help() {
  const [toolCount, setToolCount] = useState<number | null>(null);

  useEffect(() => {
    fetchTools()
      .then((t) => setToolCount(t.length))
      .catch(() => setToolCount(null));
  }, []);

  const mcpConfig = `{
  "mcpServers": {
    "pdf-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\\\Dev\\\\repos\\\\pdf-mcp", "run", "python", "run_server.py"]
    }
  }
}`;

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="help-page">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Help</h2>
        <p className="text-sm text-zinc-300 mt-1">
          {toolCount === null ? "PDF intelligence server" : `PDF intelligence server — ${toolCount} tools available`}
        </p>
      </div>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="help-overview">
        <div className="flex items-center gap-2 mb-3">
          <LifeBuoy size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">What this is</h3>
        </div>
        <p className="text-sm text-zinc-300">
          pdf-mcp extracts, manipulates, annotates, converts, validates, redacts, and RAG-searches PDFs entirely on your machine. Start in
          the{" "}
          <a className="text-amber-400 hover:text-amber-300" href="/workbench">
            Workbench
          </a>{" "}
          to open a PDF, or the{" "}
          <a className="text-amber-400 hover:text-amber-300" href="/chat">
            Chat
          </a>{" "}
          to ask questions once a local LLM is running.
        </p>
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="help-shortcuts">
        <div className="flex items-center gap-2 mb-3">
          <Keyboard size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Keyboard shortcuts</h3>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {shortcuts.map((s) => (
              <tr key={s.keys} className="border-b border-zinc-800/50">
                <td className="py-2 pr-4 font-mono text-amber-400/90 whitespace-nowrap">{s.keys}</td>
                <td className="py-2 text-zinc-300">{s.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="help-docs">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Documentation</h3>
        </div>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {docs.map((d) => (
            <li key={d.href}>
              <a
                href={d.href}
                className="flex items-center gap-2 text-sm text-zinc-300 hover:text-amber-400"
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={13} /> {d.label}
              </a>
            </li>
          ))}
          <li>
            <a
              href="/llms-full.txt"
              className="flex items-center gap-2 text-sm text-zinc-300 hover:text-amber-400"
              target="_blank"
              rel="noreferrer"
            >
              <FileCode size={13} /> Full LLM reference
            </a>
          </li>
        </ul>
      </section>

      <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6" data-testid="help-mcp-config">
        <div className="flex items-center gap-2 mb-3">
          <Terminal size={16} className="text-amber-500" />
          <h3 className="text-lg font-semibold text-zinc-100">Use from an MCP client</h3>
        </div>
        <p className="text-sm text-zinc-300 mb-2">Add this to your Claude Desktop / Cursor config to get the tools natively:</p>
        <pre className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-sm text-zinc-200 overflow-x-auto font-mono">{mcpConfig}</pre>
      </section>
    </div>
  );
}
