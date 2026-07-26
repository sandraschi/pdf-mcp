import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, Image, Table, Type, Hash, Link, RotateCw, Lock, Download, Stamp, Highlighter, FileCode, Palette } from "lucide-react";
import { uploadPdf } from "@/lib/api";

const toolTabs = [
  { id: "extract", label: "Extract", icon: FileText, tools: [
    { id: "text", label: "Text", icon: Type },
    { id: "images", label: "Images", icon: Image },
    { id: "tables", label: "Tables", icon: Table },
    { id: "metadata", label: "Metadata", icon: Hash },
    { id: "fonts", label: "Fonts", icon: Link },
  ]},
  { id: "manipulate", label: "Manipulate", icon: RotateCw, tools: [
    { id: "rotate", label: "Rotate", icon: RotateCw },
    { id: "compress", label: "Compress", icon: FileCode },
    { id: "encrypt", label: "Encrypt", icon: Lock },
  ]},
  { id: "annotate", label: "Annotate", icon: Stamp, tools: [
    { id: "watermark", label: "Watermark", icon: Stamp },
    { id: "highlight", label: "Highlight", icon: Highlighter },
  ]},
  { id: "convert", label: "Convert", icon: Download, tools: [
    { id: "to-markdown", label: "To Markdown", icon: FileCode },
    { id: "to-images", label: "To Images", icon: Palette },
  ]},
];

export default function Workbench() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ job_id: string; pages: number; size: number } | null>(null);
  const [activeTab, setActiveTab] = useState("extract");
  const [toolResult, setToolResult] = useState<string | null>(null);
  const dropRef = useRef<HTMLDivElement>(null);

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
    } catch (e) {
      setToolResult(`Upload failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
    setUploading(false);
  };

  useEffect(() => {
    const handleDragOver = (e: DragEvent) => { e.preventDefault(); };
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
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 bg-amber-500 text-black rounded-lg text-sm font-medium hover:bg-amber-400 transition-colors disabled:opacity-50"
                data-testid="upload-btn"
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
              <button
                onClick={() => { setFile(null); setUploadResult(null); setToolResult(null); }}
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
                onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
              />
            </label>
          </div>
        )}
      </div>

      {uploadResult && (
        <div className="flex-1 flex gap-4 min-h-0">
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center justify-center text-zinc-600">
            <div className="text-center space-y-2">
              <FileText size={48} className="mx-auto text-zinc-700" />
              <p className="text-sm">{file?.name}</p>
              <p className="text-xs">{uploadResult.pages} pages</p>
            </div>
          </div>

          <div className="w-72 bg-zinc-900 border border-zinc-800 rounded-xl flex flex-col overflow-hidden">
            <div className="flex border-b border-zinc-800">
              {toolTabs.map((tab) => (
                <button
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
              {toolTabs.find((t) => t.id === activeTab)?.tools.map((tool) => (
                <button
                  key={tool.id}
                  onClick={() => setToolResult(`Running ${tool.label} on ${file?.name}...`)}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
                >
                  <tool.icon size={16} className="text-zinc-500" />
                  {tool.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {toolResult && (
        <div className="mt-4 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <pre className="text-sm text-zinc-400 whitespace-pre-wrap">{toolResult}</pre>
        </div>
      )}
    </div>
  );
}
