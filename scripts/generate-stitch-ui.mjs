import { stitch } from "@google/stitch-sdk";

const prompt = `Design a local-first desktop/web app UI for "AI Knowledge Agent".

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
- Configure model/provider/API key.`;

if (!process.env.STITCH_API_KEY && !(process.env.STITCH_ACCESS_TOKEN && process.env.GOOGLE_CLOUD_PROJECT)) {
  console.error("Missing Stitch auth. Set STITCH_API_KEY, or STITCH_ACCESS_TOKEN plus GOOGLE_CLOUD_PROJECT.");
  process.exit(1);
}

const createResult = await stitch.callTool("create_project", {
  title: "AI Knowledge Agent UI",
});

const projectName = createResult?.project?.name ?? createResult?.name;
const projectId = projectName?.split("/").pop() ?? createResult?.project?.projectId ?? createResult?.projectId;

if (!projectId) {
  console.log(JSON.stringify({ createResult }, null, 2));
  throw new Error("Could not determine Stitch project id from create_project response.");
}

const project = stitch.project(projectId);
const screen = await project.generate(prompt, "DESKTOP");

const htmlUrl = await screen.getHtml();
const imageUrl = await screen.getImage();

console.log(JSON.stringify({
  projectId,
  screenId: screen.id,
  htmlUrl,
  imageUrl,
}, null, 2));
