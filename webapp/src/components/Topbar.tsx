import { useStore } from "@/lib/store";

export default function Topbar() {
  const pageTitle = useStore((s) => s.pageTitle);
  const backendOk = useStore((s) => s.backendOk);
  const backendStatus = useStore((s) => s.backendStatus);

  return (
    <header className="flex items-center justify-between px-6 h-14 bg-zinc-900 border-b border-zinc-800">
      <h1 className="text-lg font-semibold text-zinc-100">{pageTitle}</h1>
      <div className="flex items-center gap-2">
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
