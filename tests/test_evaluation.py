import json
import os
import time

from ai_knowledge_agent.config import AppConfig
from ai_knowledge_agent.evaluation import list_eval_results, run_eval
from ai_knowledge_agent.services import IndexService


def test_run_eval_uses_config_and_writes_stats(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "note.md").write_text("Chunks store filename and chunk index.", encoding="utf-8")
    questions = tmp_path / "questions.json"
    questions.write_text(
        json.dumps(
            [
                {
                    "question": "What do chunks store?",
                    "expected_answer": "filename and chunk index",
                    "source_doc": "note.md",
                }
            ]
        ),
        encoding="utf-8",
    )
    config = AppConfig(
        data_dir=tmp_path,
        raw_dir=raw_dir,
        index_dir=tmp_path / "index",
        config_dir=tmp_path / "config",
        logs_dir=tmp_path / "logs",
    )
    IndexService(config).rebuild_index(raw_dir)

    report = run_eval(config, questions, tmp_path / "results")
    previous = tmp_path / "results" / "eval-previous.json"
    previous.write_text(
        json.dumps(
            {
                "metrics": {
                    "case_count": 2,
                    "retrieval_hit_rate": 0.5,
                    "average_latency_seconds": 1.5,
                }
            }
        ),
        encoding="utf-8",
    )
    now = time.time()
    os.utime(previous, (now - 10, now - 10))
    os.utime(report["output_path"], (now, now))
    history = list_eval_results(tmp_path / "results")

    assert report["metrics"]["case_count"] == 1
    assert report["index_stats"]["indexed_chunks"] == 1
    assert history[0]["case_count"] == 1
    assert history[0]["retrieval_hit_rate"] == 1.0
    assert history[0]["comparison"]["previous_filename"] == "eval-previous.json"
    assert history[0]["comparison"]["retrieval_hit_rate_delta"] == 0.5
    assert history[0]["comparison"]["case_count_delta"] == -1
