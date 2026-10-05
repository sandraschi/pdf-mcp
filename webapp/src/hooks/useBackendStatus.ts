import { useStore } from "@/lib/store";
import { useEffect } from "react";

/**
 * Tauri backend bridge.
 *
 * `src-tauri/src/backend.rs` emits a `backend-status: "ready"` event once the
 * bundled backend has bound its port. Inside the Tauri WebView we listen for it
 * and refresh health immediately; in a plain browser this is a no-op (the
 * AppLayout health poll covers that case).
 */
export function useBackendStatus() {
  const healthCheck = useStore((s) => s.healthCheck);

  useEffect(() => {
    const w = window as unknown as { __TAURI__?: unknown; __TAURI_INTERNALS__?: unknown };
    if (!w.__TAURI__ && !w.__TAURI_INTERNALS__) return;

    let unlisten: (() => void) | undefined;
    let cancelled = false;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        const un = await listen<string>("backend-status", () => healthCheck());
        if (cancelled) un();
        else unlisten = un;
      } catch {
        /* Tauri event API unavailable — HTTP poll still covers health */
      }
    })();

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [healthCheck]);
}
