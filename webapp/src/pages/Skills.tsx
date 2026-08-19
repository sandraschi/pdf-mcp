import { fetchSkillContent, fetchSkills } from "@/lib/api";
import { motion } from "framer-motion";
import { BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function renderMarkdown(text: string) {
  return text
    .split("\n")
    .map((line) => {
      const safe = escapeHtml(line);
      if (line.startsWith("### ")) return `<h3 class="text-base font-semibold text-zinc-100 mt-4 mb-2">${escapeHtml(line.slice(4))}</h3>`;
      if (line.startsWith("## ")) return `<h2 class="text-lg font-semibold text-amber-500 mt-5 mb-2">${escapeHtml(line.slice(3))}</h2>`;
      if (line.startsWith("# ")) return `<h1 class="text-xl font-bold text-zinc-100 mt-5 mb-3">${escapeHtml(line.slice(2))}</h1>`;
      if (line.startsWith("- ")) return `<li class="text-sm text-zinc-400 ml-4 list-disc">${escapeHtml(line.slice(2))}</li>`;
      if (line.startsWith("> "))
        return `<blockquote class="border-l-2 border-amber-500/50 pl-3 text-zinc-500 italic text-sm my-2">${escapeHtml(line.slice(2))}</blockquote>`;
      if (line.startsWith("```")) return `<pre class="bg-zinc-800 rounded-lg p-3 text-xs text-zinc-300 overflow-x-auto my-2 font-mono">`;
      if (line.trim() === "") return "<br />";
      if (/^`[^`]+`$/.test(line.trim()))
        return `<code class="bg-zinc-800 px-1.5 py-0.5 rounded text-xs text-amber-400 font-mono">${escapeHtml(line.trim().slice(1, -1))}</code>`;
      return `<p class="text-sm text-zinc-400 my-1">${safe}</p>`;
    })
    .join("\n");
}

export default function Skills() {
  const [skills, setSkills] = useState<Array<{ name: string; description: string }>>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSkills()
      .then(setSkills)
      .catch(() => {});
  }, []);

  const handleExpand = async (name: string) => {
    if (expanded === name) {
      setExpanded(null);
      setContent(null);
      return;
    }
    setExpanded(name);
    setLoading(true);
    try {
      const c = await fetchSkillContent(name);
      setContent(c);
    } catch {
      setContent("Failed to load skill content.");
    }
    setLoading(false);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="skills">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Skills</h2>
        <p className="text-sm text-zinc-500 mt-1">Available MCP skills and instructions</p>
      </div>

      {skills.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-600">
          <BookOpen size={48} className="mb-3 opacity-50" />
          <p className="text-sm">No skills available</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="skills-list">
          {skills.map((skill) => {
            const isExpanded = expanded === skill.name;
            return (
              <motion.div
                key={skill.name}
                data-testid="skill-item"
                className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <button
                  type="button"
                  onClick={() => handleExpand(skill.name)}
                  className="w-full flex items-center justify-between px-5 py-4 hover:bg-zinc-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/10 rounded-lg">
                      <BookOpen size={16} className="text-amber-500" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium text-zinc-100">{skill.name}</p>
                      {skill.description && <p className="text-xs text-zinc-500 mt-0.5">{skill.description}</p>}
                    </div>
                  </div>
                  {isExpanded ? <ChevronDown size={16} className="text-zinc-500" /> : <ChevronRight size={16} className="text-zinc-500" />}
                </button>

                {isExpanded && (
                  <div className="px-5 pb-4 border-t border-zinc-800 pt-3" data-testid="skill-content">
                    {loading ? (
                      <div className="animate-pulse space-y-2">
                        <div className="h-4 bg-zinc-800 rounded w-3/4" />
                        <div className="h-4 bg-zinc-800 rounded w-1/2" />
                      </div>
                    ) : content ? (
                      // biome-ignore lint/security/noDangerouslySetInnerHtml: content is HTML-escaped by renderMarkdown before injection
                      <div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
                    ) : (
                      <p className="text-sm text-zinc-500">No content</p>
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
