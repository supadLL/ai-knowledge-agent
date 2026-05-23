from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from .config import AppConfig
from .services import AnswerService, IndexService


def run_eval(
    config: AppConfig,
    questions_path: Path,
    results_dir: Path,
) -> dict:
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    index_service = IndexService(config)
    answer_service = AnswerService(index_service)
    started = time.perf_counter()
    cases = []

    for item in questions:
        result = answer_service.ask(item["question"], top_k=config.top_k)
        expected_source = item.get("source_doc")
        hit = bool(
            expected_source
            and any(expected_source.lower() in source.chunk.filename.lower() for source in result.sources)
        )
        cases.append(
            {
                "question": item["question"],
                "expected_source": expected_source,
                "retrieved": [
                    {
                        "chunk_id": source.chunk.id,
                        "filename": source.chunk.filename,
                        "score": round(source.score, 4),
                    }
                    for source in result.sources
                ],
                "retrieval_hit": hit,
                "answer": result.answer,
            }
        )

    elapsed = time.perf_counter() - started
    metrics = {
        "case_count": len(cases),
        "retrieval_hit_rate": round(
            sum(1 for case in cases if case["retrieval_hit"]) / len(cases), 4
        )
        if cases
        else 0,
        "average_latency_seconds": round(elapsed / len(cases), 4) if cases else 0,
    }
    report = {
        "metrics": metrics,
        "index_stats": asdict(index_service.stats()),
        "cases": cases,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    output = results_dir / f"eval-{int(time.time() * 1000)}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["output_path"] = str(output)
    return report


def list_eval_results(results_dir: Path) -> list[dict]:
    if not results_dir.exists():
        return []
    results = []
    paths = sorted(results_dir.glob("eval-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        metrics = report.get("metrics") if isinstance(report, dict) else {}
        if not isinstance(metrics, dict):
            metrics = {}
        results.append(
            {
                "filename": path.name,
                "path": str(path),
                "created_at": int(path.stat().st_mtime),
                "case_count": int(metrics.get("case_count") or 0),
                "retrieval_hit_rate": float(metrics.get("retrieval_hit_rate") or 0),
                "average_latency_seconds": float(metrics.get("average_latency_seconds") or 0),
            }
        )
    for index, result in enumerate(results):
        previous = results[index + 1] if index + 1 < len(results) else None
        result["comparison"] = compare_eval_result(result, previous) if previous else None
    return results


def compare_eval_result(current: dict, previous: dict) -> dict:
    return {
        "previous_filename": previous["filename"],
        "retrieval_hit_rate_delta": round(
            current["retrieval_hit_rate"] - previous["retrieval_hit_rate"], 4
        ),
        "average_latency_seconds_delta": round(
            current["average_latency_seconds"] - previous["average_latency_seconds"], 4
        ),
        "case_count_delta": current["case_count"] - previous["case_count"],
    }
