# RAG Design Notes

The retrieval pipeline starts by loading local documents and normalizing text. Text is split into stable chunks with a configurable chunk size and overlap.

Each chunk stores metadata including filename, file path, document id, and chunk index. Citations use the document filename and chunk index so users can inspect where an answer came from.

The MVP uses local lexical retrieval to keep the first build dependency-light. Later builds can add embeddings, vector search, reranking, and grounded LLM generation without changing the user-facing workflow.

Evaluation measures retrieval hit rate, citation correctness, latency, and answer quality. The first eval runner focuses on retrieval hit rate and latency.
