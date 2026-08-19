import { useEffect, useState } from "react";

const ZOOM_LEVELS = [0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0];
const STORAGE_KEY = "tauri-zoom";

function readSavedZoom(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const v = Number(raw);
    return ZOOM_LEVELS.includes(v) ? v : 1.0;
  } catch {
    return 1.0;
  }
}

export function useZoom() {
  const [zoom, setZoom] = useState<number>(readSavedZoom);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(zoom));
    } catch {
      /* private mode */
    }
    const root = document.getElementById("app-root");
    if (root) root.style.zoom = String(zoom);
  }, [zoom]);

  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      const idx = ZOOM_LEVELS.indexOf(zoom);
      if (e.deltaY < 0 && idx < ZOOM_LEVELS.length - 1) setZoom(ZOOM_LEVELS[idx + 1]);
      if (e.deltaY > 0 && idx > 0) setZoom(ZOOM_LEVELS[idx - 1]);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && (e.key === "0" || e.key === "num0")) {
        e.preventDefault();
        setZoom(1.0);
      }
    };
    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKey);
    };
  }, [zoom]);

  return { zoom };
}
