# GitHub Copilot Instructions (pdf-mcp)

## Session Context (pdf-mcp)

pdf-mcp is a PDF intelligence MCP server (FastMCP 3.4.4, Starlette HTTP on port
11131, React webapp on port 11130). Before starting work: run `pdf_status` to
confirm the server is alive and `pdf_help` to see the current tool surface. The 10
tools are pdf_extract, pdf_manipulate, pdf_annotate, pdf_forms, pdf_convert,
pdf_validate, pdf_rag, pdf_help, pdf_status, pdf_shutdown. Each domain tool is a
portmanteau with an `operation` param - read the docstring for operation names. At
end of work: save any generated PDFs to data/uploads/ and note the job_id in the
thread.

## Standards

- Python: ruff + pyright, all gates via `just ci`
- Webapp: React + Vite + Tailwind + Zustand; `bun`, not npm
- Never commit `.env` or secrets
