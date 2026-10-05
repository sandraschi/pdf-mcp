# pdf-mcp — User Guide

This guide is for someone who has just installed **pdf-mcp** and wants to get real work
done with it. It walks through installation, first calls, end-to-end workflows, the webapp,
troubleshooting, and a set of worked dialogues you can imitate. It assumes no prior
knowledge of the MCP protocol beyond the fact that you talk to a set of named tools.

If you only read one section, read **Quick start** and then **Workflows**.

---

## Quick start

pdf-mcp runs in two modes.

**stdio mode (for Claude Desktop / Cursor).** Add this to your MCP client's config:

```json
{
  "mcpServers": {
    "pdf-mcp": {
      "command": "uv",
      "args": ["--directory", "D:\\Dev\\repos\\pdf-mcp", "run", "python", "run_server.py"]
    }
  }
}
```

The server starts, registers its sixteen tools, and waits on stdio. No ports are used.

**HTTP mode (for the webapp or REST clients).**

```powershell
cd D:\Dev\repos\pdf-mcp
uv sync
uv run python run_server.py --mode http --port 11131
```

The backend listens on `http://127.0.0.1:11131`. To also run the React webapp:

```powershell
cd webapp
bun install
bun run dev
```

Then open `http://127.0.0.1:11130`. On Windows you can skip both steps and run
`.\start.ps1`, which starts the backend and frontend and opens the browser.

**Recommended first calls.** Ask the server what it can do, then confirm it is healthy:

```
pdf_status()
pdf_help()
```

`pdf_status` returns `{success, server, version, uptime_seconds, tool_count, mode}`.
`pdf_help` returns the list of tools; `pdf_help(tool_name="pdf_extract")` returns the input
schema for one tool.

---

## The mental model

There are two kinds of tools:

1. **Read tools** that inspect a PDF and return data: `pdf_extract`, `pdf_analyze`,
   `pdf_validate`, `pdf_rag(search)`, `pdf_classify`, `pdf_dedupe`. These are safe to call
   as often as you like.
2. **Write tools** that produce a new file: `pdf_manipulate`, `pdf_annotate`,
   `pdf_convert`, `pdf_redact`, `pdf_export`, and the `index` operation of `pdf_rag`. These
   return a path in the upload directory; the original is untouched.

A few tools straddle the line: `pdf_forms(fill)` writes a file but needs `list_fields`
first; `pdf_do` may call anything.

The other distinction that matters is **LLM or not**. `pdf_do`, `pdf_annotate(summary_box)`,
`pdf_forms(auto_fill)`, `pdf_classify(refine=true)`, and `pdf_rag(synthesize)` use a local
LLM if one is present. Everything else works with no LLM at all. If you do not have Ollama
or LM Studio installed, ignore those four operations and the server is still fully useful
for extraction, conversion, validation, redaction, and RAG search (which uses a local
embedding model, not a chat model).

---

## Workflow: understand an unknown PDF

You have a PDF of unknown provenance and you want to know what you are dealing with before
doing anything else.

1. **Classify the medium.** `pdf_analyze(path)`. If `scanned` is true, the document is
   image-only and text extraction will come back nearly empty. You will need OCR (outside
   this server) before extraction, redaction, or indexing are meaningful. If `layout_hint`
   is `digital`, proceed.
2. **Read the metadata.** `pdf_extract(operation="metadata", path=...)` gives title, author,
   dates, and page count — useful for naming outputs and for compliance.
3. **Read the opening text.** `pdf_extract(operation="text", path=..., pages="1-3")`. This is
   cheap and tells you the document's shape faster than reading all of it.
4. **Check the structure.** `pdf_extract(operation="outline", path=...)` returns the table of
   contents if the PDF has one. `pdf_extract(operation="tables", path=...)` finds tabular
   content.
5. **Decide.** Now you know whether to convert, extract images, fill a form, or index.

A worked dialogue:

> **User:** What's in `quarterly.pdf`?
>
> **Assistant:** `pdf_analyze(path="D:/docs/quarterly.pdf")` → `{scanned: false,
> layout_hint: "digital", pages: 24, chars_per_page: 1800}`. It's a digital 24-page
> document. `pdf_extract(operation="metadata", path=...)` → title "Q3 Financial Report",
> author "Finance". `pdf_extract(operation="outline", path=...)` → sections: Summary,
> Revenue, Costs, Outlook. I can summarise it, extract the tables, or answer questions
> against it — which would you like?

---

## Workflow: batch-convert a folder of PDFs to Markdown

You have twenty PDFs and you want one Markdown file each.

Because there is no folder-globbing tool, you drive the loop yourself: list the files, then
call `pdf_convert(operation="to_markdown", path=...)` once per file. Each call returns
`{success, markdown, pages, message}`; the Markdown is in the response, and the server also
writes a converted artefact to its upload directory where the tool supports it. Save each
`markdown` field to `<name>.md` on your side.

If you want this as an unattended pipeline instead, use the HTTP server: drop the PDFs into
`data/watch/`, and the `ingest` recipe runs analyze → index → export_brief on each new file
automatically. Watch progress in the webapp's Pipeline page or via `GET /api/watch/status`.

Tips:

- Convert with `pdf_convert(to_markdown)` when you want prose; use
  `pdf_extract(operation="text")` when you want plain text without heading detection.
- If a document is scanned, conversion returns almost nothing useful. Run `pdf_analyze`
  first and skip or OCR the scanned ones.
- Keep the `pages` field from the response so you can verify you got the whole document.

---

## Workflow: make a searchable knowledge base

You have a set of reference PDFs and you want to ask questions across all of them.

1. **Index each document.** `pdf_rag(operation="index", path=...)`. This chunks the text
   (table-aware), embeds the chunks, and writes them to LanceDB. The call returns
   `{chunks_indexed, doc_id}`. Note the `doc_id` — you will need it to delete the document
   later.
2. **Confirm the index.** `pdf_rag(operation="list_documents")` returns every indexed
   document with its chunk count.
3. **Search.** `pdf_rag(operation="search", query="termination clause", limit=8)`. Each hit
   carries `{doc_id, chunk_id, page_num, section, source_file, text, _distance}`. The
   `source_file` and `page_num` let you jump to the source.
4. **Query by example.** If you have a paragraph and want passages like it, pass it as
   `text` to `pdf_rag(operation="similar")`.
5. **Synthesise.** `pdf_rag(operation="synthesize", query="What are the payment terms
   across these contracts?")` groups hits by document and, if a local LLM is available,
   writes a grounded answer with per-document evidence. Without an LLM you still get the
   grouped hits, which you can read yourself.
6. **Prune.** `pdf_rag(operation="delete_index", doc_id=...)` removes a document when it is
   superseded.

Important cost note: indexing is the expensive step (embedding every chunk); searching is
cheap. Index once, search many times. If you re-index the same file, delete the old
`doc_id` first to avoid duplicates.

---

## Workflow: redact before sharing

You need to remove names, emails, and account numbers before sending a PDF externally.

1. **Copy first.** Redaction is irreversible on the output file. Keep the original.
2. **Know your PII.** `pdf_redact(path=..., pii=true)` targets emails, phone numbers, IBANs,
   card numbers, US SSNs, and IP addresses. If you also have specific terms (a client name,
   an internal codename), pass them in `terms`.
3. **Run it.** The call returns `{path, occurrences}`. Review `occurrences` to see how many
   matches were found.
4. **Verify.** Extract the text of the redacted file and search for the terms you redacted.
   `pdf_extract(operation="text", path=<redacted>)` then check it is clean.
5. **Optional hardening.** `pdf_manipulate(operation="flatten")`-style flattening via
   `pdf_forms` or a re-save via `pdf_manipulate(operation="optimize")` can strip residual
   metadata. Confirm nothing sensitive remains in `pdf_extract(operation="metadata")`.

A caution that recurs in this guide: never index a document into LanceDB before checking
whether it contains secrets, because the vector store is local but persistent.

---

## Workflow: fill a form from a source document

You have a blank form PDF and a source document containing the values.

1. `pdf_forms(operation="list_fields", path=<form>)` — get the exact field names.
2. Either fill manually with `pdf_forms(operation="fill", path=<form>,
   fields={"name": "...", ...})`, or let the LLM do the mapping:
   `pdf_forms(operation="auto_fill", path=<form>, source=<source-pdf>)` (or `text="..."` for
   free text). It returns `{path, filled, missing}`.
3. Read `missing` — those fields could not be matched and need manual attention.
4. Optionally `pdf_forms(operation="flatten", path=<filled>)` so the values are no longer
   editable.
5. Export the values for a record: `pdf_forms(operation="export_data", path=<filled>)`.

If `auto_fill` is unavailable (no local LLM), fall back to `fill` with explicit values.

---

## Workflow: comply and compare

Before publishing or archiving, you want to know the document is well-formed and accessible.

1. `pdf_validate(operation="integrity", path=...)` — every page reads without error.
2. `pdf_validate(operation="accessibility", path=...)` — a 0-100 score. Low scores usually
   mean a missing language tag, no tagged structure, or images without alt text. The server
   can tell you which, but it cannot add the missing structure; that is an authoring fix.
3. `pdf_validate(operation="pdfa", path=...)` — PDF/A indicators from metadata.
4. `pdf_validate(operation="structure", path=...)` — headings, paragraphs, and content
   issues.
5. To compare two versions: `pdf_validate(operation="compare", path_a=..., path_b=...)`
   returns `{same_page_count, text_similarity, diffs}`. The `diffs` list shows where the
   text diverges.

---

## Workflow: build a document brief

When you need a short, reusable summary of a long document:

`pdf_export(path=..., format="markdown", include_summary=true)`. Without a local LLM it
still produces a structured brief (headings, key terms); with one it adds an LLM summary.
The result is `{path, pages, summary}`. Use `format="json"` when the brief will feed another
program.

This is also the last step of the `ingest` and `redact_export` recipes, so if you are
running the HTTP pipeline you get briefs for free.

---

## The webapp

The React operator UI on port **11130** has seven pages:

- **Dashboard** — server version, tool count, uptime, an LLM-availability banner, a hero
  explaining the app, and a usage panel (operations run, jobs, files).
- **Workbench** — a PDF.js viewer with an OCR (scanned/digital) badge, a side-by-side
  compare mode, and a tool palette (Extract, Manipulate, Annotate, Convert). Upload a PDF,
  click a tool, and the job runs; results download from the palette.
- **Pipeline** — upload a file, run a single operation or a multi-step recipe, and watch the
  job history. Completed jobs expose a 24-hour share link.
- **Chat** — local-LLM chat with a skill-first system prompt, a personality selector, a
  provider/model picker, and a "Search PDFs" pane that turns RAG hits into clickable
  citations that jump to the page in the Workbench.
- **Tools** — live discovery of the MCP tool surface via `/api/tools`, with drill-down into
  each tool's sub-operations and input schema.
- **Skills** — renders the server's `SKILL.md` content.
- **Logs** — a live tail of the server's ring-buffer log.

Keyboard shortcuts: `Ctrl+Scroll` zooms (persisted), `Ctrl+0` resets zoom, `Ctrl+L` opens
Logs, `Ctrl+H` opens Tools, `Ctrl+K` focuses the Chat PDF search. The sidebar carries a
backend status dot that turns green when the backend answers.

### Connecting chat to a local model

Chat, summaries, auto-fill, and `pdf_do` need a local chat model. Start **Ollama**
(`ollama serve`, default port 11434) or **LM Studio** (default port 1234). The webapp
auto-detects either on load and lists the models it finds. If none is running, the Chat
page says so and the Dashboard shows an optional setup prompt; every other page keeps
working.

---

## HTTP and the REST API

When in HTTP mode the server exposes more than the MCP endpoint. A few you will use often:

- `GET /api/health` — is it up?
- `GET /api/tools` — the tool surface as JSON.
- `POST /api/pdf/upload` — multipart upload; returns a `job_id`.
- `POST /api/jobs` — `{operation, params}` or `{recipe, params}`.
- `GET /api/jobs/{job_id}` — status and step log.
- `POST /api/rag/search` — `{query, limit}`; synchronous RAG for citations.
- `GET /api/stats` — per-operation usage counters.

Recipes are `ingest`, `redact_export`, and `brief`. `POST /api/jobs` with
`{"recipe": "ingest", "params": {"filename": "report.pdf"}}` runs the whole chain.

---

## Troubleshooting

**"The backend is offline" (red dot).** The frontend cannot reach `http://127.0.0.1:11131`.
Start the backend (`uv run python run_server.py --mode http --port 11131`) or run
`.\start.ps1`. Check `/api/health` directly. If the port is occupied by a stale process,
stop it before restarting.

**Chat says "No local LLM detected".** Start Ollama (`ollama serve`) or LM Studio, then
reload the page. Only the LLM-assisted operations are affected; extraction, conversion,
validation, redaction, and RAG search continue to work.

**Extraction returns almost no text.** The document is scanned. Confirm with `pdf_analyze`;
if `scanned` is true, OCR the document elsewhere first. This stack is text-layer oriented.

**`pdf_rag(search)` returns nothing.** Either nothing is indexed
(`pdf_rag(list_documents)` will be empty) or the query vocabulary does not match. Index the
document first (`pdf_rag(index, path=...)`), then search. Remember that indexing needs the
optional RAG extra (`uv sync --extra rag`) for real sentence-transformer embeddings; without
it the server falls back to a lightweight hash embedding that is far less accurate.

**`pdf_forms(fill)` changes nothing.** You probably used the wrong field names. Run
`list_fields` and match exactly, including case and punctuation.

**A manipulate/annotate call succeeded but I cannot find the file.** Every write tool stores
its output in the upload directory (`data/uploads` by default) and returns the full path in
its response. Read the `path` field.

**Redaction missed something.** `pdf_redact` matches patterns (and any `terms` you pass); a
name written as an image, or with unusual spacing, may not match. Extraction-based
verification (step 4 of the redaction workflow) is the safety net.

**`pdf_do` does nothing.** It needs a local LLM to plan. Start Ollama or LM Studio, or
sequence the tools yourself.

**Everything is slow on the first RAG call.** The embedding model loads on first use and the
first query pays that cost. Subsequent calls are fast.

**Port 11131 already in use.** Another pdf-mcp instance (or an unrelated process) holds it.
Identify and stop it, or run the backend on a different `--port` and point the frontend at
it.

---

## Worked dialogues

### Dialogue 1 — split and extract

> **User:** Split `report.pdf` into single pages and give me the text of page 4.
>
> **Assistant:** `pdf_manipulate(operation="split", path="D:/docs/report.pdf")` →
> `{success: true, files: [...], message: "Split 12 pages."}`. Then
> `pdf_extract(operation="text", path="D:/docs/report.pdf", pages="4")` → the text of page 4.
> The split files are in the upload directory; here is the page-4 text.

### Dialogue 2 — find and redact

> **User:** Does `contract.pdf` contain email addresses, and can you remove them?
>
> **Assistant:** `pdf_redact(path="D:/docs/contract.pdf", pii=true)` →
> `{success: true, path: "..._redacted.pdf", occurrences: 7}`. Seven PII matches were
> blackened. I verified the redacted copy with `pdf_extract(operation="text")` — the emails
> are gone. The redacted file is `..._redacted.pdf`; the original is untouched.

### Dialogue 3 — answer across documents

> **User:** Across the three policy PDFs, what is the retention period?
>
> **Assistant:** First I index them: `pdf_rag(operation="index", path=...)` for each (three
> calls, `doc_ids` noted). Then `pdf_rag(operation="synthesize", query="data retention
> period")` → grouped hits by document and a synthesised answer: the retention period is 7
> years, cited from `retention_policy.pdf` p.4 and confirmed in `privacy_policy.pdf` p.9.
> Here are the two source passages.

### Dialogue 4 — validate and compare

> **User:** I edited `report_v1.pdf` into `report_v2.pdf`. What changed?
>
> **Assistant:** `pdf_validate(operation="compare", path_a="...v1.pdf",
> path_b="...v2.pdf")` → `{same_page_count: true, text_similarity: 0.83, diffs: [...]}`.
> Same page count, 83% textual overlap. The diffs show three changed paragraphs — the
> executive summary, the Q3 figure, and the outlook section. Want me to run `pdf_validate`
> accessibility on both?

### Dialogue 5 — classify a folder

> **User:** Tell me what kinds of documents are in this set.
>
> **Assistant:** I'll classify each. For `a.pdf`: `pdf_classify(path="...")` → invoice
> (confidence 0.9). `b.pdf` → receipt (0.95). `c.pdf` → contract (0.8). Two of the three are
> financial documents; `c.pdf` would benefit from `pdf_forms(list_fields)` if it has fields.

---

## Housekeeping and limits

- **The job queue is in-memory.** Restarting the HTTP server clears job history (though
  output files remain on disk).
- **Share links expire after 24 hours.** Create a new one if needed.
- **The log ring buffer is bounded** (500 entries); older entries roll off. Use the Logs
  page or `GET /api/logs?level=error` to filter.
- **Uploads accumulate.** Clean `data/uploads` periodically; nothing prunes it
  automatically.
- **The vector store persists** in `data/lancedb`. Delete a `doc_id` with
  `pdf_rag(delete_index)` when a document is superseded.

---

## Getting help

- `pdf_help()` lists every tool; `pdf_help(tool_name="pdf_rag")` shows that tool's schema.
- `pdf_status()` confirms the server is healthy.
- The `skill://pdf-expert` skill carries a compact operation catalogue.
- The repository's `docs/TOOLS.md` and `llms-full.txt` mirror the tool and endpoint
  reference.

---

## Workflow: build a compliance packet

You are assembling an audit packet: a set of source PDFs, redacted, validated, and indexed.

For each source document, in this order:

1. `pdf_analyze(path=...)` — record whether it is scanned. A scanned document cannot be
   redacted by text matching, so flag it for manual handling.
2. `pdf_validate(operation="integrity", path=...)` — confirm it is not corrupt before you
   invest in it.
3. `pdf_redact(path=..., pii=true)` — produce the clean copy. Record `occurrences`.
4. `pdf_extract(operation="text", path=<redacted>)` — verify no PII remains. This is the
   audit evidence that the redaction worked.
5. `pdf_validate(operation="accessibility", path=<redacted>)` — record the score for the
   packet summary.
6. `pdf_rag(operation="index", path=<redacted>)` — make the clean copy searchable, recording
   its `doc_id`.
7. `pdf_export(path=<redacted>, format="markdown", include_summary=true)` — produce the
   brief that heads the packet.

At the end, `pdf_rag(operation="list_documents")` gives you the packet manifest with chunk
counts, and `pdf_validate(operation="compare")` against a previous packet shows what
changed. The whole sequence is deterministic except the LLM summary, so you can re-run it
and diff the results.

---

## Workflow: prepare a document for print or email

1. `pdf_manipulate(operation="optimize", path=...)` to clean the structure.
2. `pdf_manipulate(operation="compress", path=<optimized>, quality=80)` to shrink it. Check
   the returned original and compressed sizes; if the reduction is negligible the document
   was already efficient.
3. `pdf_validate(operation="integrity", path=<compressed>)` to confirm nothing broke.
4. If it will be emailed to an external party, `pdf_redact(pii=true)` first.
5. `pdf_annotate(operation="watermark", text="DRAFT")` if it is not final.

A practical note: compression mostly removes redundant image data. A text-only PDF will not
shrink much, and that is expected; do not run compression repeatedly hoping for a different
result.

---

## Workflow: turn a scan into a usable text artefact

This server is text-layer oriented, so a pure image scan is a hard boundary. The honest
workflow is:

1. `pdf_analyze(path=...)` — confirm `scanned: true`.
2. OCR the document **outside** pdf-mcp (for example with Tesseract or an online service).
3. Re-check the OCR'd PDF with `pdf_analyze` — it should now report a text layer.
4. From here the normal tools apply: `pdf_extract(text)`, `pdf_validate(integrity)`,
   `pdf_rag(index)`, and so on.

Do not index a scanned document and expect search to find its content; there are no text
chunks to embed.

---

## Frequently asked questions

**Does pdf-mcp upload my documents anywhere?** No. Extraction, manipulation, redaction,
validation, and embedding all run locally. The only network calls are to a local LLM
(`127.0.0.1:11434` for Ollama or `127.0.0.1:1234` for LM Studio) when you use an
LLM-assisted operation, and those are loopback.

**Can I use it entirely offline?** Yes, for everything except the LLM-assisted operations.
Ollama itself is offline once a model is pulled; LM Studio likewise. Embeddings use a local
model, not a cloud API, unless you deliberately set `RAG_EMBEDDING_URL`.

**Which embedding model does search use?** `all-MiniLM-L6-v2` by default, configurable via
`RAG_EMBEDDING_MODEL`. If the optional `rag` extra is not installed, the server falls back to
a lightweight hash embedding that is much less accurate — install
`uv sync --extra rag` for real semantic search.

**Does redaction remove text from the underlying file, or just draw black boxes?** It
blackens the content in the output PDF. Verify with extraction before you rely on it. Treat
the output as the authoritative clean copy and keep the original separately.

**Can I change the ports?** Yes. Set `MCP_PORT` and `FRONTEND_PORT`, or pass `--port` to the
server. If you change them, update the frontend's target and the CORS origin accordingly.
The defaults are backend 11131 and frontend 11130.

**Where do output files go?** Into the upload directory, `data/uploads` by default,
configurable via `UPLOAD_DIR`. Every write tool returns the full path.

**How do I back up the search index?** Copy `data/lancedb` (or your `RAG_STORE_PATH`). The
index is self-contained; restoring the directory restores search.

**What happens if two people index the same file?** The `doc_id` is derived from the file
path, so re-indexing the same path overwrites rather than duplicates. Indexing a copy at a
different path creates a separate `doc_id`.

**Is there a size limit on PDFs?** Practical limits are memory and time, not a hard cap.
Very large files are best handled a page range at a time for extraction, and indexing scales
with total chunk count.

**Can it OCR?** No. pdf-mcp detects scanned documents and works with existing text layers;
OCR is out of scope by design.

---

## Glossary

- **Portmanteau tool** — one MCP tool exposing many operations selected by an `operation`
  argument.
- **Text layer** — the selectable text embedded in a PDF. Digital PDFs have one; scans do
  not.
- **Scanned PDF** — an image-only document; `pdf_analyze` reports `scanned: true`.
- **RAG** — retrieval-augmented generation: index text chunks, retrieve the closest, and
  optionally synthesise an answer.
- **Chunk** — a slice of document text sized for embedding and retrieval.
- **Embedding** — a numeric vector representing a chunk's meaning, used for semantic search.
- **doc_id** — the stable identifier of an indexed document; needed to delete its index.
- **Share link** — a 24-hour tokenised URL to a completed pipeline result.
- **Recipe** — a named multi-step pipeline (`ingest`, `redact_export`, `brief`).
- **Watch folder** — `data/watch/`; new PDFs dropped here run the `ingest` recipe
  automatically.
- **Flatten** — bake form-field values into the page so they cannot be edited.
- **PII patterns** — the built-in redaction targets: email, phone, IBAN, card, SSN, IP.

---

## Performance and tuning

- **First RAG call is slow.** The embedding model loads into memory on first use. Budget for
  it once, then it is fast.
- **Index in batches off-peak.** Indexing a large corpus is the heaviest thing the server
  does; run it when you are not also rendering images.
- **Lower DPI for thumbnails.** `pdf_convert(to_images, dpi=100)` is dramatically cheaper
  than 300 dpi and is plenty for previews.
- **Compress once.** Repeated compression of an already-compressed file yields little and
  can soften images further.
- **Search with a limit.** `limit=8` is usually enough to answer a question; large limits
  return more context than a model can use and cost more tokens.
- **Delete superseded documents.** `pdf_rag(delete_index, doc_id=...)` keeps the store small
  and searches crisp.

---

## More worked dialogues

### Dialogue 6 — scanned document

> **User:** Extract the text from `scan.pdf`.
>
> **Assistant:** `pdf_analyze(path="D:/docs/scan.pdf")` → `{scanned: true,
> has_text_layer: false, chars_per_page: 0}`. This is an image-only scan, so there is no
> text layer to extract — `pdf_extract` would return essentially nothing. You'll need to OCR
> it first (Tesseract or similar); once it has a text layer I can extract, redact, validate,
> and index it.

### Dialogue 7 — make it searchable

> **User:** I want to be able to ask questions about `handbook.pdf`.
>
> **Assistant:** I'll index it first. `pdf_rag(operation="index",
> path="D:/docs/handbook.pdf")` → `{chunks_indexed: 214, doc_id: "9f2a..."}`. It's indexed.
> Now ask me anything about it — I'll search (`pdf_rag(search)`) and, if you want a written
> answer, synthesise (`pdf_rag(synthesize)`).

### Dialogue 8 — compress for email

> **User:** This 40 MB PDF is too big to email.
>
> **Assistant:** `pdf_manipulate(operation="compress", path="D:/docs/big.pdf", quality=70)` →
> `{path: "..._compressed.pdf", original_size: 41943040, compressed_size: 5242880}`. It's
> down to about 5 MB — a fifth of the original. `pdf_validate(operation="integrity")`
> confirms all pages still read. If the images look too soft at quality 70, I can retry at
> 85 for a larger but sharper file.

### Dialogue 9 — forms

> **User:** Fill this tax form with my details: Jane Doe, Vienna, income 42000.
>
> **Assistant:** First `pdf_forms(operation="list_fields", path="D:/docs/tax.pdf")` → fields:
> name, city, income, signature. Then `pdf_forms(operation="fill", path="D:/docs/tax.pdf",
> fields={"name": "Jane Doe", "city": "Vienna", "income": "42000"})` →
> `{path: "..._filled.pdf", filled: 3}`. `signature` is left blank because you did not give
> a value — fill it manually and I can `flatten` the result so it's no longer editable.

### Dialogue 10 — duplicates

> **User:** I think I keep downloading the same invoice.
>
> **Assistant:** `pdf_dedupe(paths=[...])` across the folder → `{exact_duplicates:
> [["inv_001.pdf", "inv_001 (1).pdf"]], near_duplicates: []}`. One exact duplicate pair.
> Want me to delete the copy, or just report the list?

---

## What pdf-mcp is not

To set expectations accurately:

- It is **not an OCR engine**. It detects scans and works with text layers; OCR is elsewhere.
- It is **not a cloud service**. There is no remote index, no telemetry, no upload.
- It is **not a viewer**. It produces files and data; the webapp renders PDFs for convenience
  but the tools never need a display.
- It is **not a form designer**. It fills and flattens existing AcroForm fields; it does not
  create forms.
- It is **not a layout editor**. It manipulates pages and adds markup; it does not reflow
  content.

Knowing these boundaries keeps you from asking the server for something it will honestly
decline, and points you at the right tool when the answer is "use OCR" or "use an editor".
