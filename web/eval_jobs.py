# -*- coding: utf-8 -*-
"""Background evaluation job manager for web requests."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from queue import Queue
from threading import RLock, Thread
from typing import Any, Callable, Deque, Dict, Optional
from uuid import uuid4


class EvaluationJobManager:
    def __init__(self, worker_count: int, evaluator: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.worker_count = max(1, int(worker_count))
        self.evaluator = evaluator
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._pending: Deque[str] = deque()
        self._lock = RLock()
        self._queue: Queue[Optional[str]] = Queue()
        self._workers = [
            Thread(target=self._worker_loop, name=f"eval-job-{index}", daemon=True)
            for index in range(self.worker_count)
        ]
        for worker in self._workers:
            worker.start()

    def submit(self, payload: Dict[str, Any]) -> str:
        job_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "payload": payload,
                "result": None,
                "error": None,
                "created_at": now,
                "started_at": None,
                "finished_at": None,
            }
            self._pending.append(job_id)
        self._queue.put(job_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            snapshot = dict(job)
            if snapshot["status"] == "queued":
                snapshot["queue_position"] = self._queue_position(job_id)
            else:
                snapshot["queue_position"] = 0
            snapshot.pop("payload", None)
            return snapshot

    def shutdown(self, wait: bool = False) -> None:
        for _ in self._workers:
            self._queue.put(None)
        if wait:
            for worker in self._workers:
                worker.join(timeout=2.0)

    def _queue_position(self, job_id: str) -> int:
        try:
            return list(self._pending).index(job_id) + 1
        except ValueError:
            return 0

    def _worker_loop(self) -> None:
        while True:
            job_id = self._queue.get()
            if job_id is None:
                return

            with self._lock:
                job = self._jobs[job_id]
                if job_id in self._pending:
                    self._pending.remove(job_id)
                job["status"] = "running"
                job["started_at"] = datetime.now(timezone.utc).isoformat()
                payload = job["payload"]

            try:
                result = self.evaluator(payload)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "failed"
                    job["error"] = str(exc)
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
            else:
                with self._lock:
                    job = self._jobs[job_id]
                    job["status"] = "succeeded"
                    job["result"] = result
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
