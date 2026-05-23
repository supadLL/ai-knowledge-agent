# AI Knowledge Agent Product Brief

AI Knowledge Agent is a local-first personal knowledge-base assistant for learners and developers.

The app imports Markdown and TXT files from local folders, parses text, splits content into chunks, builds a persistent local index, and answers user questions with source citations.

The first interface is a CLI because it is fast to test and easy to package later. A local web or desktop UI can reuse the same core pipeline.

User data should live in predictable local directories. Source documents, indexes, config, logs, and evaluation results should stay outside any future installed application directory so upgrades do not delete user data.

The product should expose clear controls for choosing document folders, rebuilding indexes, asking questions, viewing citations, checking logs, and diagnosing missing API keys or broken indexes.
