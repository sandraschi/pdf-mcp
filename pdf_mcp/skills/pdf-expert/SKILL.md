# pdf-mcp Skill

## Overview

pdf-mcp is a full-stack PDF intelligence MCP server. It provides 40+ operations across 7 portmanteau tools for extracting, manipulating, annotating, converting, validating, and RAG-searching PDF documents. Use it whenever the user needs to work with PDF files programmatically.

## Tool Categories

### pdf_extract — Extract content from PDFs
- `text` — extract plain text from one or more pages
- `images` — extract embedded images with dimensions and format info
- `tables` — extract tabular data via pdfplumber
- `metadata` — extract title, author, dates, page count, file size
- `fonts` — list fonts used in the document
- `links` — extract hyperlinks with page and coordinates
- `outline` — extract table of contents as a nested tree

### pdf_manipulate — Modify PDF structure
- `merge` — combine multiple PDFs into one
- `split` — split into individual pages or page ranges
- `rotate` — rotate pages by specified angle
- `reorder` — rearrange pages in a new order
- `delete_pages` — remove specific pages
- `compress` — reduce file size via image downscaling
- `encrypt` — password-protect a PDF
- `decrypt` — remove password protection
- `optimize` — clean and deflate the PDF structure

### pdf_annotate — Add markup and annotations
- `watermark` — add text or image watermark (tile, center, corner positions)
- `stamp` — add stamp annotation at specific coordinates
- `highlight` — highlight all occurrences of search text
- `underline` — underline all occurrences of search text
- `header_footer` — add repeating header and footer text
- `page_numbers` — add page numbers with configurable position and start

### pdf_forms — Handle form fields
- `list_fields` — enumerate all interactive form fields
- `fill` — fill form fields with values
- `flatten` — flatten form fields (make them non-interactive)
- `export_data` — export field values as JSON

### pdf_convert — Convert between formats
- `to_markdown` — extract text with heading detection as Markdown
- `to_images` — render each page as PNG or JPEG
- `to_html` — extract text as simple HTML
- `from_html` — create PDF from HTML content
- `from_markdown` — create PDF from Markdown content
- `from_images` — create PDF from image files (one per page)

### pdf_validate — Audit PDF quality
- `pdfa` — check PDF/A compliance via metadata
- `structure` — analyze headings, paragraphs, and content issues
- `accessibility` — score 0-100 for language, tags, alt-text
- `integrity` — verify all pages are readable without errors
- `compare` — diff text content between two PDFs

### pdf_rag — Build and query a RAG index
- `chunk` — split PDF text into chunks (recursive or fixed strategy)
- `index` — chunk and index into LanceDB vector store
- `search` — semantic search across indexed chunks
- `list_documents` — list all indexed documents with chunk counts
- `delete_index` — remove an indexed document

## Best Practices

- **Extract before manipulating**: Use `pdf_extract` to understand a document's structure before applying manipulations.
- **Use page ranges efficiently**: Operations support page ranges (e.g. "1-5,7,9-12") to target specific sections.
- **Compress after merging**: Merging large documents increases file size — run compress afterward.
- **Validate accessibility early**: Run `pdf_validate(operation="accessibility")` before distribution to catch missing language tags or heading structure.
- **Index for repeated queries**: The `pdf_rag` tool persists chunks to LanceDB — re-running `search` is cheaper than re-processing the full PDF.
- **Use `from_markdown` for clean PDFs**: Creating PDFs from Markdown produces better results than from raw HTML.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| MCP_MODE | stdio | Server transport mode |
| MCP_PORT | 11131 | HTTP port when in http mode |
| RAG_EMBEDDING_URL | (none) | OpenAI-compatible embedding API |
| RAG_EMBEDDING_MODEL | all-MiniLM-L6-v2 | Embedding model name |
