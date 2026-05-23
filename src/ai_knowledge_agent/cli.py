from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .config import AppConfig
from .evaluation import run_eval
from .services import AnswerService, IndexService


def cmd_index(args: argparse.Namespace, config: AppConfig) -> int:
    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Source does not exist: {source}")
        return 1
    result = IndexService(config).rebuild_index(source)
    print(f"Indexed {result.chunk_count} chunks from {result.source}")
    print(f"Index written to {result.index_path}")
    print(f"Embedding provider: {result.embedding_provider} ({result.embedding_dimensions} dims)")
    return 0


def cmd_ask(args: argparse.Namespace, config: AppConfig) -> int:
    index_service = IndexService(config)
    chunks = index_service.load_chunks()
    if not chunks:
        print(f"No index found at {index_service.index_path()}. Run `aka index ./data/raw` first.")
        return 1
    result = AnswerService(index_service).ask(args.question, top_k=args.top_k)
    print(result.answer)
    if result.sources:
        print("\nSources:")
        for source in result.sources:
            print(
                f"- {source.chunk.filename}#{source.chunk.index} "
                f"score={source.score:.4f} path={source.chunk.path}"
            )
    return 0


def cmd_eval(args: argparse.Namespace, config: AppConfig) -> int:
    questions_path = Path(args.questions).resolve()
    if not questions_path.exists():
        print(f"Eval questions file does not exist: {questions_path}")
        return 1
    report = run_eval(
        config,
        questions_path,
        Path("evals/results"),
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"Saved eval report to {report['output_path']}")
    return 0


def cmd_diagnose(_args: argparse.Namespace, config: AppConfig) -> int:
    index_service = IndexService(config)
    print(json.dumps(asdict(index_service.stats()), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aka", description="AI Knowledge Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index .md and .txt files")
    index_parser.add_argument("source", help="File or folder to index")
    index_parser.set_defaults(func=cmd_index)

    ask_parser = subparsers.add_parser("ask", help="Ask a question against the local index")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=None)
    ask_parser.set_defaults(func=cmd_ask)

    eval_parser = subparsers.add_parser("eval", help="Run retrieval evaluation")
    eval_parser.add_argument("--questions", default="evals/questions.json")
    eval_parser.set_defaults(func=cmd_eval)

    diagnose_parser = subparsers.add_parser("diagnose", help="Show local data/index status")
    diagnose_parser.set_defaults(func=cmd_diagnose)
    return parser


def main() -> int:
    config = AppConfig.from_env()
    config.ensure_dirs()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
