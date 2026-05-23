# Stitch UI Design Prompt

This document captures the Stitch prompt for the first UI design pass of AI Knowledge Agent.

## Goal

Generate a polished desktop UI design for a local-first personal RAG knowledge-base app.

## Prompt

```text
Design a local-first desktop/web app UI for "AI Knowledge Agent".

Audience: individual learners and developers building a personal RAG knowledge base.

Product goals:
- Import local Markdown/TXT folders.
- Build a persistent local index.
- Ask questions with source citations.
- Run evaluation questions.
- Inspect logs and diagnostics.
- Configure model/provider/API key status.
- Prepare for a Windows-first packaged release.

Create a polished desktop dashboard screen.

Visual direction:
- Work-focused SaaS/productivity style.
- Dense but calm.
- Practical, trustworthy, local-first.
- Avoid a marketing hero layout.
- Prioritize scanability, practical controls, and citation trust.

Layout requirements:
- Left navigation with Documents, Ask, Evaluations, Settings, Diagnostics.
- Main screen should show document folder and index status.
- Include a prominent question input.
- Include retrieved citation cards.
- Include an answer panel with source chips.
- Include eval metrics.
- Include local data health and diagnostics.

Interaction cues:
- Folder selection.
- Rebuild index.
- Ask question.
- Open source citation.
- Run eval set.
- View logs.
- Configure model/provider/API key.
```

## Run

Set `STITCH_API_KEY`, install the SDK if needed, then run:

```powershell
cd E:\ai-play\ai-knowledge-agent
npm install @google/stitch-sdk
$env:STITCH_API_KEY = "your-key"
node .\scripts\generate-stitch-ui.mjs
```

The script prints the Stitch project result plus the generated screen's HTML and screenshot URLs.
