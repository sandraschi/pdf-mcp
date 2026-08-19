import { fetchChat, fetchSkillContent, fetchSkills } from "@/lib/api";
import { useStore } from "@/lib/store";
import { motion } from "framer-motion";
import { Cpu, Download, Eraser, MessageSquare, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "pdf-mcp-chat-history";
const PERSONALITY_KEY = "pdf-mcp-chat-personality";
const MAX_MSGS = 100;

const personalities = [
  {
    id: "research-assistant",
    label: "Research Assistant",
    prompt: "You are a thorough research assistant helping with PDF analysis and document understanding.",
  },
  {
    id: "expert-reviewer",
    label: "Expert Reviewer",
    prompt: "You are an expert reviewer who provides critical analysis of document content.",
  },
  {
    id: "quick-summarizer",
    label: "Quick Summarizer",
    prompt: "You provide concise summaries of documents, extracting key points efficiently.",
  },
  {
    id: "technical-writer",
    label: "Technical Writer",
    prompt: "You are a technical writer who helps craft clear documentation from source material.",
  },
];

const examplePrompts = [
  {
    category: "Analysis",
    items: [
      "Summarize the key findings in this PDF",
      "Extract all tables from the document",
      "Identify the main arguments and conclusions",
    ],
  },
  {
    category: "Extraction",
    items: ["Extract all images from this PDF", "List all fonts used in the document", "Get metadata from the PDF"],
  },
  {
    category: "Conversion",
    items: ["Convert this PDF to markdown", "Split the PDF into individual pages", "Merge these PDFs into one document"],
  },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  ts?: string;
}

function loadHistory(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(msgs: Message[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-MAX_MSGS)));
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>(loadHistory);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [personality, setPersonality] = useState(() => localStorage.getItem(PERSONALITY_KEY) || "research-assistant");
  const [skillText, setSkillText] = useState("");

  const providers = useStore((s) => s.providers);
  const llmAvailable = useStore((s) => s.llmAvailable);
  const llmProbing = useStore((s) => s.llmProbing);
  const llmProvider = useStore((s) => s.llmProvider);
  const llmModel = useStore((s) => s.llmModel);
  const setLlmProvider = useStore((s) => s.setLlmProvider);
  const setLlmModel = useStore((s) => s.setLlmModel);
  const discoverLlm = useStore((s) => s.discoverLlm);

  useEffect(() => {
    discoverLlm();
  }, [discoverLlm]);

  useEffect(() => {
    let cancelled = false;
    fetchSkills()
      .then((skills) => {
        if (!skills.length || cancelled) return;
        return fetchSkillContent(skills[0].name);
      })
      .then((content) => {
        if (content && !cancelled) setSkillText(content.slice(0, 3000));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  useEffect(() => {
    localStorage.setItem(PERSONALITY_KEY, personality);
  }, [personality]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim(), ts: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const p = personalities.find((p) => p.id === personality);
    const systemPrompt = `You are a PDF document assistant. ${p?.prompt || ""}\n\nRelevant skill context:\n${skillText}`;

    try {
      const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));
      const res = await fetchChat([{ role: "system", content: systemPrompt }, ...history], personality, llmProvider, llmModel);
      const assistantMsg: Message = { role: "assistant", content: res.content, ts: new Date().toISOString() };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e instanceof Error ? e.message : "Request failed"}`, ts: new Date().toISOString() },
      ]);
    }
    setLoading(false);
  }, [input, loading, messages, personality, skillText, llmProvider, llmModel]);

  const handleExport = () => {
    if (messages.length === 0) return;
    const text = messages.map((m) => `[${m.ts ? new Date(m.ts).toISOString() : ""}] ${m.role.toUpperCase()}: ${m.content}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pdf-mcp-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClear = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div className="h-full flex flex-col" data-testid="chat-page">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Chat</h2>
        </div>
        <div className="flex items-center gap-2" data-testid="chat-controls">
          <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-zinc-800/60 border border-zinc-800" data-testid="llm-status">
            <Cpu size={14} className={llmAvailable ? "text-green-400" : llmProbing ? "text-amber-400 animate-pulse" : "text-zinc-600"} />
            <span className={`text-xs ${llmAvailable ? "text-green-400" : "text-zinc-500"}`}>
              {llmProbing ? "probing..." : llmAvailable ? (llmProvider === "ollama" ? "Ollama" : "LM Studio") : "no LLM"}
            </span>
          </div>
          {llmAvailable && (
            <>
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
                data-testid="llm-provider-select"
              >
                {Object.entries(providers)
                  .filter(([, v]) => v.available)
                  .map(([id, v]) => (
                    <option key={id} value={id}>
                      {v.name}
                    </option>
                  ))}
              </select>
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500 max-w-56"
                data-testid="llm-model-select"
              >
                {(providers[llmProvider]?.models || []).map((m) => (
                  <option key={m} value={m}>
                    {m.length > 34 ? `${m.slice(0, 31)}...` : m}
                  </option>
                ))}
              </select>
            </>
          )}
          <select
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-amber-500"
            data-testid="personality-select"
          >
            {personalities.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleExport}
            disabled={messages.length === 0}
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors disabled:opacity-30"
            data-testid="chat-export"
            title="Export chat"
          >
            <Download size={16} />
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={messages.length === 0}
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors disabled:opacity-30"
            data-testid="chat-clear"
            title="Clear chat"
          >
            <Eraser size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl flex flex-col min-h-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat-messages">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <MessageSquare size={48} className="text-zinc-700" />
              <p className="text-zinc-500 text-sm">Ask questions about your PDF documents</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <motion.div
              key={`${msg.ts ?? "msg"}-${i}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                  msg.role === "user" ? "bg-amber-500/10 text-zinc-100 border border-amber-500/20" : "bg-zinc-800 text-zinc-300"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </motion.div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-zinc-800 rounded-xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-zinc-800" data-testid="example-prompts">
          <div className="flex flex-wrap gap-2 mb-3">
            {examplePrompts
              .flatMap((g) => g.items.slice(0, 2))
              .map((prompt) => (
                <button
                  type="button"
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  className="px-3 py-1.5 bg-zinc-800 rounded-lg text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 transition-colors"
                >
                  {prompt}
                </button>
              ))}
          </div>
        </div>

        <div className="px-4 py-3 border-t border-zinc-800">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask about your PDF..."
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-amber-500"
              data-testid="chat-input"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="px-4 py-2.5 bg-amber-500 text-black rounded-lg text-sm font-medium hover:bg-amber-400 transition-colors disabled:opacity-50"
              data-testid="chat-send"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
