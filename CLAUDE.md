# pdf-mcp — Claude / agent context

PDF intelligence MCP. Ports **11130** (frontend) / **11131** (backend).

## Do

- Prefer portmanteau tools (`pdf_extract`, `pdf_manipulate`, …)
- Use workbench/pipeline for interactive jobs; RAG for corpus Q&A
- Follow `docs/ONBOARDING.md` / `SPEC.md`

## Don't

- Index confidential PDFs without Sandra's intent
- Assume cloud OCR is wired
- Commit `data/` uploads or LanceDB indexes

## Commands

```powershell
.\start.ps1
just test
just lint
```

See AGENTS.md, SPEC.md, llms-full.txt.
