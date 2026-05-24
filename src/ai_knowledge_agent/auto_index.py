from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import AppConfig
from .document_sources import DocumentSource, DocumentSourceStore
from .services import IndexService


SUPPORTED_AUTO_INDEX_EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True)
class AutoIndexScanResult:
    source_id: str
    label: str
    path: str
    changed: bool
    indexed: bool
    chunk_count: int = 0
    error: str | None = None


class AutoIndexService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.source_store = DocumentSourceStore(config.config_dir)
        self.index_service = IndexService(config)

    def status(self) -> dict:
        sources = self.source_store.list_sources()
        return {
            "supported_extensions": sorted(SUPPORTED_AUTO_INDEX_EXTENSIONS),
            "enabled_sources": sum(1 for source in sources if source.auto_index_enabled),
            "sources": [asdict(source) for source in sources],
        }

    def scan_once(self) -> list[AutoIndexScanResult]:
        results = []
        for source in self.source_store.list_sources():
            if not source.auto_index_enabled:
                continue
            results.append(self.scan_source(source))
        return results

    def scan_source(self, source: DocumentSource) -> AutoIndexScanResult:
        try:
            fingerprint = fingerprint_source(Path(source.path))
            changed = fingerprint != (source.last_auto_fingerprint or "")
            if not changed:
                return AutoIndexScanResult(
                    source_id=source.id,
                    label=source.label,
                    path=source.path,
                    changed=False,
                    indexed=False,
                    chunk_count=source.last_chunk_count,
                )
            result = self.index_service.replace_source_index(Path(source.path))
            self.source_store.mark_auto_index_result(
                source.id,
                fingerprint=fingerprint,
                chunk_count=result.chunk_count,
            )
            return AutoIndexScanResult(
                source_id=source.id,
                label=source.label,
                path=source.path,
                changed=True,
                indexed=True,
                chunk_count=result.chunk_count,
            )
        except Exception as error:
            message = " ".join(str(error).split())[:500]
            self.source_store.mark_auto_index_result(
                source.id,
                fingerprint=source.last_auto_fingerprint,
                chunk_count=source.last_chunk_count,
                error=message,
            )
            return AutoIndexScanResult(
                source_id=source.id,
                label=source.label,
                path=source.path,
                changed=True,
                indexed=False,
                chunk_count=source.last_chunk_count,
                error=message,
            )


class AutoIndexWorker:
    def __init__(self, config: AppConfig, interval_seconds: int = 10) -> None:
        self.config = config
        self.interval_seconds = max(2, interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="auto-index", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        AutoIndexService(self.config).scan_once()
        while not self._stop.wait(self.interval_seconds):
            AutoIndexService(self.config).scan_once()


def fingerprint_source(path: Path) -> str:
    if path.is_file():
        files = [path] if path.suffix.lower() in SUPPORTED_AUTO_INDEX_EXTENSIONS else []
    else:
        files = [
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() in SUPPORTED_AUTO_INDEX_EXTENSIONS
        ]
    payload = []
    for item in sorted(files, key=lambda candidate: str(candidate.resolve()).lower()):
        stat = item.stat()
        payload.append(
            {
                "path": str(item.resolve()),
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
            }
        )
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
