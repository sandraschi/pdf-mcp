import { API_BASE, analyzeFile, compareFiles, submitJob, uploadPdf } from "@/lib/api";
import {
  Columns2,
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
import { useSearchParams } from "react-router-dom";

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
  const [searchParams] = useSearchParams();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ job_id: string; pages: number; size: number } | null>(null);
  const [activeTab, setActiveTab] = useState("extract");
  const [toolResult, setToolResult] = useState<string | null>(null);
  const [resultJobId, setResultJobId] = useState<string | null>(null);
  const [runningTool, setRunningTool] = useState<string | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [analysis, setAnalysis] = useState<{
    has_text_layer: boolean;
    scanned: boolean;
    layout_hint: string;
    chars_per_page: number;
  } | null>(null);
  const [compare, setCompare] = useState(false);
  const [compareFile, setCompareFile] = useState<File | null>(null);
  const [compareResult, setCompareResult] = useState<string | null>(null);
  const [jumpHint, setJumpHint] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const canvasBRef = useRef<HTMLCanvasElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  const fileUrl = uploadResult && file ? `${API_BASE}/api/pdf/files/${encodeURIComponent(file.name)}` : null;
  const fileUrlB = compare && compareFile ? `${API_BASE}/api/pdf/files/${encodeURIComponent(compareFile.name)}` : null;

  // Load ?file=&page= deep link (citation jump from Chat)
  // biome-ignore lint/correctness/useExhaustiveDependencies: mount-only deep-link load
  useEffect(() => {
    const linkedFile = searchParams.get("file");
    const linkedPage = Number(searchParams.get("page") || "1");
    if (linkedFile) {
      setFile(new File([], linkedFile, { type: "application/pdf" }));
      setUploadResult({ job_id: "", pages: 0, size: 0 });
      setPageNum(linkedPage > 0 ? linkedPage : 1);
      setJumpHint(true);
    }
  }, []);

  const renderPdfPage = useCallback(async (url: string, canvas: HTMLCanvasElement | null, page: number) => {
    if (!url || !canvas) return;
    try {
      const doc = await pdfjsLib.getDocument(url).promise;
      const pg = await doc.getPage(Math.min(page, doc.numPages));
      const viewport = pg.getViewport({ scale: 1.5 });
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await pg.render({ canvasContext: ctx, viewport }).promise;
    } catch {
      /* render fallback to metadata */
    }
  }, []);

  useEffect(() => {
    if (fileUrl) renderPdfPage(fileUrl, canvasRef.current, pageNum);
  }, [fileUrl, pageNum, renderPdfPage]);

  useEffect(() => {
    if (fileUrlB) renderPdfPage(fileUrlB, canvasBRef.current, pageNum);
  }, [fileUrlB, pageNum, renderPdfPage]);

  // OCR analysis badge
  useEffect(() => {
    if (!uploadResult || !file || uploadResult.pages === 0) return;
    let cancelled = false;
    analyzeFile(file.name)
      .then((a) => {
        if (!cancelled && a.success)
          setAnalysis({
            has_text_layer: a.has_text_layer,
            scanned: a.scanned,
            layout_hint: a.layout_hint,
            chars_per_page: a.chars_per_page,
          });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [uploadResult, file]);

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
      setJumpHint(false);
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

  const runCompare = async () => {
    if (!compareFile || !file) return;
    setCompareResult(null);
    try {
      if (compareFile.name !== file.name) {
        await uploadPdf(compareFile);
      }
      const result = await compareFiles(file.name, compareFile.name);
      if (!result.success) {
        setCompareResult(result.error || "compare failed");
        return;
      }
      const lines = [
        `Page count: ${result.same_page_count ? "same" : "DIFFERS"}`,
        `Text similarity: ${(result.text_similarity * 100).toFixed(1)}%`,
        ...(result.diffs || []).slice(0, 15).map((d) => d.slice(0, 160)),
      ];
      setCompareResult(lines.join("\n"));
    } catch (e) {
      setCompareResult(`Compare failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
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
          <p className="text-sm text-zinc-500 mt-1">View, compare, and process PDF documents</p>
        </div>
        {jumpHint && (
          <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-1.5">
            Linked from chat - upload to view page
          </span>
        )}
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
                  setCompare(false);
                  setCompareFile(null);
                }}
                className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-lg text-sm hover:bg-zinc-700 transition-colors"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={() => setCompare((c) => !c)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-colors ${
                  compare ? "bg-amber-500 text-black" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                }`}
                data-testid="compare-toggle"
              >
                <Columns2 size={14} /> Compare
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
          <div className="flex-1 grid grid-cols-1 gap-4 min-w-0" style={compare ? { gridTemplateColumns: "1fr 1fr" } : undefined}>
            <div className="flex flex-col min-h-0 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden" data-testid="pdf-viewer">
              <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
                <p className="text-xs text-zinc-400 truncate">{file?.name}</p>
                {analysis && (
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                      analysis.scanned ? "bg-amber-500/15 text-amber-400" : "bg-green-500/15 text-green-400"
                    }`}
                    data-testid="ocr-badge"
                  >
                    {analysis.scanned ? "Scanned" : "Digital"} · {analysis.chars_per_page} ch/pg
                  </span>
                )}
              </div>
              <div className="flex-1 p-4 overflow-auto flex flex-col items-center justify-center gap-3">
                {fileUrl ? (
                  <>
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
                  </>
                ) : (
                  <div className="text-center space-y-2">
                    <FileText size={48} className="mx-auto text-zinc-700" />
                    <p className="text-sm">{jumpHint ? "Upload this file to view it." : file?.name}</p>
                    {jumpHint && (
                      <button type="button" onClick={handleUpload} className="px-3 py-1.5 bg-amber-500 text-black rounded-lg text-sm">
                        Upload now
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {compare && (
              <div
                className="flex flex-col min-h-0 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
                data-testid="compare-viewer"
              >
                <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between gap-2">
                  {compareFile ? (
                    <p className="text-xs text-zinc-400 truncate">{compareFile.name}</p>
                  ) : (
                    <label className="flex items-center gap-1.5 text-xs text-zinc-300 cursor-pointer hover:text-amber-400">
                      <Upload size={12} /> Choose second PDF
                      <input
                        type="file"
                        accept="application/pdf"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) setCompareFile(f);
                        }}
                      />
                    </label>
                  )}
                  {compareFile && (
                    <button
                      type="button"
                      onClick={runCompare}
                      className="text-[11px] px-2 py-1 bg-amber-500 text-black rounded font-medium hover:bg-amber-400"
                      data-testid="run-compare"
                    >
                      Compare
                    </button>
                  )}
                </div>
                <div className="flex-1 p-4 overflow-auto flex flex-col items-center gap-2">
                  <canvas ref={canvasBRef} className="max-w-full h-auto shadow-lg rounded" />
                  {compareResult && (
                    <pre className="w-full text-[11px] text-zinc-400 whitespace-pre-wrap bg-zinc-800/60 rounded p-2 max-h-40 overflow-auto">
                      {compareResult}
                    </pre>
                  )}
                </div>
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
