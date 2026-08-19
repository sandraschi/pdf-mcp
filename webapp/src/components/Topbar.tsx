import { useStore } from "@/lib/store";

export default function Topbar({ zoom }: { zoom?: number }) {
  const pageTitle = useStore((s) => s.pageTitle);
  const backendOk = useStore((s) => s.backendOk);
  const backendStatus = useStore((s) => s.backendStatus);

  return (
    <header className="flex items-center justify-between px-6 h-14 bg-zinc-900 border-b border-zinc-800">
      <h1 className="text-lg font-semibold text-zinc-100">{pageTitle}</h1>
      <div className="flex items-center gap-3">
        {zoom !== undefined && (
          <span className="text-xs text-zinc-500 font-mono" data-testid="zoom-indicator" title="Ctrl+scroll to zoom, Ctrl+0 to reset">
            {Math.round(zoom * 100)}%
          </span>
        )}
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            backendOk === null ? "bg-zinc-500" : backendOk ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
          data-testid="topbar-dot"
        />
        <span className="text-xs text-zinc-500">
          {backendStatus === "connecting" ? "Connecting..." : backendStatus === "connected" ? "Connected" : "Offline"}
        </span>
      </div>
    </header>
  );
}
