import { API_BASE, submitJob, uploadPdf } from "@/lib/api";
import {
  Download,
  FileCode,
  FileText,
  Hash,
  Highlighter,
  Image,
  Link,
  Loader2,
  Lock,
  Palette,
  RotateCw,
  Stamp,
  Table,
  Type,
  Upload,
} from "lucide-react";
import * as pdfjsLib from "pdfjs-dist";
import { useCallback, useEffect, useRef, useState } from "react";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

const toolTabs = [
  {
    id: "extract",
    label: "Extract",
    icon: FileText,
    tools: [
      { id: "text", label: "Text", icon: Type },
      { id: "images", label: "Images", icon: Image },
      { id: "tables", label: "Tables", icon: Table },
      { id: "metadata", label: "Metadata", icon: Hash },
      { id: "fonts", label: "Fonts", icon: Link },
    ],
  },
  {
    id: "manipulate",
    label: "Manipulate",
    icon: RotateCw,
    tools: [
      { id: "rotate", label: "Rotate", icon: RotateCw },
      { id: "compress", label: "Compress", icon: FileCode },
      { id: "encrypt", label: "Encrypt", icon: Lock },
    ],
  },
  {
    id: "annotate",
    label: "Annotate",
    icon: Stamp,
    tools: [
      { id: "watermark", label: "Watermark", icon: Stamp },
      { id: "highlight", label: "Highlight", icon: Highlighter },
    ],
  },
  {
    id: "convert",
    label: "Convert",
    icon: Download,
    tools: [
      { id: "to-markdown", label: "To Markdown", icon: FileCode },
      { id: "to-images", label: "To Images", icon: Palette },
    ],
  },
];

const OPERATION_MAP: Record<string, string> = {
  text: "extract_text",
  images: "extract_images",
  tables: "extract_tables",
  metadata: "extract_metadata",
  fonts: "extract_fonts",
  rotate: "rotate",
  compress: "compress",
  encrypt: "encrypt",
  watermark: "watermark",
  highlight: "highlight",
  "to-markdown": "convert_markdown",
  "to-images": "to_images",
};

export default function Workbench() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ job_id: string; pages: number; size: number } | null>(null);
  const [activeTab, setActiveTab] = useState("extract");
  const [toolResult, setToolResult] = useState<string | null>(null);
  const [resultJobId, setResultJobId] = useState<string | null>(null);
  const [runningTool, setRunningTool] = useState<string | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  const fileUrl = uploadResult && file ? `${API_BASE}/api/pdf/files/${encodeURIComponent(file.name)}` : null;

  useEffect(() => {
    if (!fileUrl || !canvasRef.current) return;
    let cancelled = false;
    (async () => {
      try {
        const doc = await pdfjsLib.getDocument(fileUrl).promise;
        if (cancelled) return;
        const page = await doc.getPage(Math.min(pageNum, doc.numPages));
        if (cancelled) return;
        const viewport = page.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch {
        /* PDF may not be renderable in-browser; fall back to metadata */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fileUrl, pageNum]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f && f.type === "application/pdf") setFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const r = await uploadPdf(file);
      setUploadResult(r);
      setPageNum(1);
    } catch (e) {
      setToolResult(`Upload failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
    setUploading(false);
  };

  const handleTool = async (toolId: string, label: string) => {
    if (!file || !uploadResult) return;
    const operation = OPERATION_MAP[toolId];
    if (!operation) {
      setToolResult(`Operation '${label}' is not wired yet.`);
      return;
    }
    setRunningTool(toolId);
    setToolResult(null);
    setResultJobId(null);
    try {
      const { job_id } = await submitJob(operation, { filename: file.name });
      setResultJobId(job_id);
      setToolResult(`Job ${job_id} submitted: ${label}. Polling...`);
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const r = await fetch(`${API_BASE}/api/jobs/${job_id}`);
        const job = await r.json();
        if (job.status === "completed") {
          setToolResult(`${label} completed.`);
          break;
        }
        if (job.status === "failed") {
          setToolResult(`${label} failed: ${job.error || "unknown error"}`);
          break;
        }
      }
    } catch (e) {
      setToolResult(`Error: ${e instanceof Error ? e.message : "Request failed"}`);
    }
    setRunningTool(null);
  };

  useEffect(() => {
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
    };
    window.addEventListener("dragover", handleDragOver);
    return () => window.removeEventListener("dragover", handleDragOver);
  }, []);

  return (
    <div className="h-full flex flex-col" data-testid="workbench">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Workbench</h2>
          <p className="text-sm text-zinc-500 mt-1">View and process PDF documents</p>
        </div>
      </div>

      <div
        ref={dropRef}
        onDrop={handleDrop}
        className="border-2 border-dashed border-zinc-700 rounded-xl p-8 text-center hover:border-amber-500/50 transition-colors mb-4"
      >
        {file ? (
          <div className="space-y-3">
            <FileText size={40} className="mx-auto text-amber-500" />
            <p className="text-zinc-100 font-medium">{file.name}</p>
            <p className="text-sm text-zinc-500">{(file.size / 1024).toFixed(0)} KB</p>
            <div className="flex gap-2 justify-center">
              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 bg-amber-500 text-black rounded-lg text-sm font-medium hover:bg-amber-400 transition-colors disabled:opacity-50"
                data-testid="upload-btn"
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  setUploadResult(null);
                  setToolResult(null);
                  setResultJobId(null);
                }}
                className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-lg text-sm hover:bg-zinc-700 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload size={40} className="mx-auto text-zinc-600" />
            <p className="text-zinc-400">Drop a PDF here or click to browse</p>
            <label className="inline-block px-4 py-2 bg-amber-500 text-black rounded-lg text-sm font-medium hover:bg-amber-400 transition-colors cursor-pointer">
              Select File
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) setFile(f);
                }}
              />
            </label>
          </div>
        )}
      </div>

      {uploadResult && (
        <div className="flex-1 flex gap-4 min-h-0">
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl p-4 overflow-auto" data-testid="pdf-viewer">
            {fileUrl ? (
              <div className="flex flex-col items-center gap-3 min-h-full justify-center">
                <canvas ref={canvasRef} className="max-w-full h-auto shadow-lg rounded" />
                <div className="flex items-center gap-3 text-sm text-zinc-400">
                  <button
                    type="button"
                    disabled={pageNum <= 1}
                    onClick={() => setPageNum((p) => p - 1)}
                    className="px-3 py-1 bg-zinc-800 rounded-lg disabled:opacity-30 hover:bg-zinc-700"
                  >
                    Prev
                  </button>
                  <span>
                    Page {pageNum} / {uploadResult.pages}
                  </span>
                  <button
                    type="button"
                    disabled={pageNum >= uploadResult.pages}
                    onClick={() => setPageNum((p) => p + 1)}
                    className="px-3 py-1 bg-zinc-800 rounded-lg disabled:opacity-30 hover:bg-zinc-700"
                  >
                    Next
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-2">
                <FileText size={48} className="mx-auto text-zinc-700" />
                <p className="text-sm">{file?.name}</p>
                <p className="text-xs">{uploadResult.pages} pages</p>
              </div>
            )}
          </div>

          <div className="w-72 bg-zinc-900 border border-zinc-800 rounded-xl flex flex-col overflow-hidden" data-testid="tool-palette">
            <div className="flex border-b border-zinc-800">
              {toolTabs.map((tab) => (
                <button
                  type="button"
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                    activeTab === tab.id ? "text-amber-500 border-b-2 border-amber-500" : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  <tab.icon size={14} className="mx-auto mb-1" />
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="flex-1 p-3 space-y-1 overflow-y-auto">
              {toolTabs
                .find((t) => t.id === activeTab)
                ?.tools.map((tool) => (
                  <button
                    type="button"
                    key={tool.id}
                    disabled={runningTool !== null}
                    onClick={() => handleTool(tool.id, tool.label)}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors disabled:opacity-40"
                  >
                    {runningTool === tool.id ? (
                      <Loader2 size={16} className="text-amber-500 animate-spin" />
                    ) : (
                      <tool.icon size={16} className="text-zinc-500" />
                    )}
                    {tool.label}
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}

      {toolResult && (
        <div className="mt-4 bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-2">
          <pre className="text-sm text-zinc-400 whitespace-pre-wrap">{toolResult}</pre>
          {resultJobId && (
            <a
              href={`${API_BASE}/api/pdf/${resultJobId}/result`}
              className="inline-flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300"
              data-testid="result-download"
            >
              <Download size={14} /> Download result
            </a>
          )}
        </div>
      )}
    </div>
  );
}
