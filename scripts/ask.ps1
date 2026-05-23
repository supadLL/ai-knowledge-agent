$ErrorActionPreference = "Stop"

$question = if ($args.Count -gt 0) { $args -join " " } else { "How does the app preserve local data?" }
python -m ai_knowledge_agent.cli ask $question
