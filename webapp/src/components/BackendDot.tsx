import { useStore } from "@/lib/store";
import { useCallback, useEffect, useRef } from "react";

const intervals = [1000, 2000, 4000, 8000, 16000];

export default function BackendDot() {
  const backendOk = useStore((s) => s.backendOk);
  const healthCheck = useStore((s) => s.healthCheck);
  const attemptRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(() => {
    healthCheck().then(() => {
      const ok = useStore.getState().backendOk;
      if (ok) {
        attemptRef.current = 0;
        timerRef.current = setTimeout(poll, 30000);
      } else {
        attemptRef.current = Math.min(attemptRef.current + 1, intervals.length - 1);
        timerRef.current = setTimeout(poll, intervals[attemptRef.current]);
      }
    });
  }, [healthCheck]);

  useEffect(() => {
    poll();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [poll]);

  return (
    <div className="flex items-center gap-2" data-testid="backend-dot">
      <div
        className={`w-2.5 h-2.5 rounded-full ${
          backendOk === null ? "bg-zinc-500" : backendOk ? "bg-green-500 animate-pulse" : "bg-red-500"
        }`}
      />
      <span className="text-xs text-zinc-500">{backendOk === null ? "Connecting..." : backendOk ? "Connected" : "Offline"}</span>
    </div>
  );
}
