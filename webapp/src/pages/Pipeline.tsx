import { API_BASE, createShare, fetchJobs, fetchRecipes, submitJob } from "@/lib/api";
import { motion } from "framer-motion";
import { FileText, Link2, Play, Upload } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const PAGE_SIZE = 10;

const operations = [
  { value: "extract_text", label: "Extract Text" },
  { value: "extract_images", label: "Extract Images" },
  { value: "extract_tables", label: "Extract Tables" },
  { value: "compress", label: "Compress PDF" },
  { value: "rotate", label: "Rotate Pages" },
  { value: "encrypt", label: "Encrypt PDF" },
  { value: "convert_markdown", label: "Convert to Markdown" },
  { value: "merge", label: "Merge PDFs" },
  { value: "split", label: "Split PDF" },
];

export default function Pipeline() {
  const [file, setFile] = useState<File | null>(null);
  const [operation, setOperation] = useState("extract_text");
  const [recipe, setRecipe] = useState("");
  const [recipes, setRecipes] = useState<Array<{ name: string; steps: string[] }>>([]);
  const [jobs, setJobs] = useState<Array<{ job_id: string; operation: string; status: string; created: string }>>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [jobSearch, setJobSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<"created" | "status" | "operation">("created");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  const loadJobs = useCallback(async () => {
    try {
      const j = await fetchJobs();
      setJobs(j);
    } catch {
      /* backend may not be ready */
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    fetchRecipes()
      .then(setRecipes)
      .catch(() => {});
  }, []);

  const handleExecute = async () => {
    if (!file) return;
    setRunning(true);
    setResult(null);
    setShareUrl(null);
    try {
      const r = await submitJob(operation, { filename: file.name });
      setResult(`Job submitted: ${r.job_id}`);
      await loadJobs();
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "Unknown"}`);
    }
    setRunning(false);
  };

  const handleRecipe = async () => {
    if (!file || !recipe) return;
    setRunning(true);
    setResult(null);
    setShareUrl(null);
    try {
      const r = await fetch(`${API_BASE}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipe, params: { filename: file.name } }),
      });
      const data = await r.json();
      setResult(`Recipe ${recipe} started: ${data.job_id}`);
      await loadJobs();
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "Unknown"}`);
    }
    setRunning(false);
  };

  const handleShare = async (jobId: string) => {
    try {
      const url = await createShare(jobId);
      setShareUrl(url);
      await navigator.clipboard.writeText(url);
      setResult(`Share link copied: ${url}`);
    } catch (e) {
      setResult(`Share failed: ${e instanceof Error ? e.message : "Unknown"}`);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "completed":
        return "text-green-400";
      case "running":
        return "text-amber-400";
      case "failed":
        return "text-red-400";
      default:
        return "text-zinc-300";
    }
  };

  const filteredJobs = useMemo(() => {
    const q = jobSearch.trim().toLowerCase();
    const list = jobs.filter((j) => {
      if (statusFilter !== "all" && j.status !== statusFilter) return false;
      if (!q) return true;
      return j.job_id.toLowerCase().includes(q) || j.operation.toLowerCase().includes(q);
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      return av < bv ? -dir : av > bv ? dir : 0;
    });
  }, [jobs, jobSearch, statusFilter, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(filteredJobs.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageJobs = filteredJobs.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const toggleSort = (key: "created" | "status" | "operation") => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="pipeline">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Pipeline</h2>
        <p className="text-sm text-zinc-300 mt-1">Batch PDF operations</p>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
        <div>
          <span className="block text-sm font-medium text-zinc-300 mb-2">PDF File</span>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 px-4 py-2.5 bg-zinc-800 rounded-lg cursor-pointer hover:bg-zinc-700 transition-colors text-zinc-300 text-sm">
              <Upload size={16} />
              {file ? file.name : "Choose file"}
              <input type="file" accept="application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </label>
            {file && (
              <button type="button" onClick={() => setFile(null)} className="text-sm text-zinc-300 hover:text-zinc-300">
                Clear
              </button>
            )}
          </div>
        </div>

        <div>
          <label htmlFor="operation-select" className="block text-sm font-medium text-zinc-300 mb-2">
            Operation
          </label>
          <select
            id="operation-select"
            value={operation}
            onChange={(e) => setOperation(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
            data-testid="operation-select"
          >
            {operations.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="recipe-select" className="block text-sm font-medium text-zinc-300 mb-2">
            Recipe (multi-step)
          </label>
          <select
            id="recipe-select"
            value={recipe}
            onChange={(e) => setRecipe(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
            data-testid="recipe-select"
          >
            <option value="">Single operation above</option>
            {recipes.map((rc) => (
              <option key={rc.name} value={rc.name}>
                {rc.name} ({rc.steps.join(" → ")})
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleExecute}
            disabled={!file || running || !!recipe}
            className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 text-black rounded-lg text-sm font-medium hover:bg-amber-400 transition-colors disabled:opacity-50"
            data-testid="execute-btn"
          >
            <Play size={16} />
            {running ? "Running..." : "Execute"}
          </button>
          <button
            type="button"
            onClick={handleRecipe}
            disabled={!file || running || !recipe}
            className="flex items-center gap-2 px-5 py-2.5 bg-zinc-800 text-zinc-200 rounded-lg text-sm font-medium hover:bg-zinc-700 transition-colors disabled:opacity-50"
            data-testid="recipe-btn"
          >
            <Play size={16} />
            Run Recipe
          </button>
        </div>

        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm text-zinc-300 bg-zinc-800/50 rounded-lg p-3 space-y-1"
          >
            <p>{result}</p>
            {shareUrl && (
              <a
                href={shareUrl}
                target="_blank"
                rel="noreferrer"
                className="text-amber-400 hover:text-amber-300 text-sm break-all"
                data-testid="share-link"
              >
                {shareUrl}
              </a>
            )}
          </motion.div>
        )}
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden" data-testid="job-history">
        <div className="px-5 py-3 border-b border-zinc-800 flex flex-wrap items-center gap-3">
          <h3 className="text-sm font-semibold text-zinc-100">Job History</h3>
          <span className="text-sm text-zinc-300">
            {filteredJobs.length} of {jobs.length}
          </span>
          <input
            value={jobSearch}
            onChange={(e) => {
              setJobSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search jobs..."
            className="ml-auto bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-amber-500"
            data-testid="job-search"
          />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
            data-testid="job-status-filter"
          >
            <option value="all">All statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-300 text-sm uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">
                  <button type="button" onClick={() => toggleSort("operation")} className="hover:text-zinc-100">
                    Operation {sortKey === "operation" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                <th className="text-left px-5 py-3 font-medium">Job ID</th>
                <th className="text-left px-5 py-3 font-medium">
                  <button type="button" onClick={() => toggleSort("status")} className="hover:text-zinc-100">
                    Status {sortKey === "status" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                <th className="text-left px-5 py-3 font-medium">
                  <button type="button" onClick={() => toggleSort("created")} className="hover:text-zinc-100">
                    Created {sortKey === "created" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                <th className="text-left px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pageJobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-zinc-300" data-testid="job-empty">
                    <FileText size={24} className="mx-auto mb-2 opacity-50" />
                    <p className="text-sm">{jobs.length === 0 ? "No jobs yet" : "No jobs match the filter"}</p>
                  </td>
                </tr>
              ) : (
                pageJobs.map((job) => (
                  <tr key={job.job_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="px-5 py-3 text-zinc-300 font-mono text-sm">{job.job_id}</td>
                    <td className="px-5 py-3 text-zinc-300">{job.operation}</td>
                    <td className={`px-5 py-3 font-medium ${statusColor(job.status)}`}>{job.status}</td>
                    <td className="px-5 py-3 text-zinc-300 text-sm">{job.created}</td>
                    <td className="px-5 py-3">
                      {job.status === "completed" && (
                        <button
                          type="button"
                          onClick={() => handleShare(job.job_id)}
                          className="flex items-center gap-1 text-sm text-amber-400 hover:text-amber-300"
                          data-testid="share-btn"
                        >
                          <Link2 size={12} /> Share
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {pageCount > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800" data-testid="job-pagination">
            <span className="text-sm text-zinc-300">
              Page {currentPage} of {pageCount}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-zinc-800 rounded-lg text-sm text-zinc-200 disabled:opacity-40 hover:bg-zinc-700"
              >
                Prev
              </button>
              <button
                type="button"
                disabled={currentPage >= pageCount}
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                className="px-3 py-1 bg-zinc-800 rounded-lg text-sm text-zinc-200 disabled:opacity-40 hover:bg-zinc-700"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
