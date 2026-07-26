const API_BASE = "http://127.0.0.1:11131";

export async function fetchHealth(): Promise<{ status: string; version: string; uptime_seconds: number; tool_count: number }> {
  const r = await fetch(`${API_BASE}/api/health`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function uploadPdf(file: File): Promise<{ job_id: string; pages: number; size: number }> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`${API_BASE}/api/pdf/upload`, { method: "POST", body: form });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchJobs(): Promise<Array<{ job_id: string; operation: string; status: string; created: string }>> {
  const r = await fetch(`${API_BASE}/api/jobs`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function submitJob(operation: string, params: Record<string, unknown>): Promise<{ job_id: string }> {
  const r = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operation, params }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchTools(): Promise<Array<{ name: string; description: string; inputSchema: Record<string, unknown> }>> {
  const r = await fetch(`${API_BASE}/api/tools`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchSkills(): Promise<Array<{ name: string; description: string }>> {
  const r = await fetch(`${API_BASE}/api/skills`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchSkillContent(name: string): Promise<string> {
  const r = await fetch(`${API_BASE}/api/skills/${name}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.text();
}

export async function fetchLogs(params?: { level?: string; search?: string; limit?: number }): Promise<Array<{ timestamp: string; level: string; source: string; message: string }>> {
  const q = new URLSearchParams();
  if (params?.level) q.set("level", params.level);
  if (params?.search) q.set("search", params.search);
  if (params?.limit) q.set("limit", String(params.limit));
  const r = await fetch(`${API_BASE}/api/logs?${q}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function fetchChat(messages: Array<{ role: string; content: string }>, personality: string): Promise<{ content: string }> {
  const r = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, personality }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
