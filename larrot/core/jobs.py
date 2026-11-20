"""Async job engine: every mutating op returns job_id, completes after jittered delay."""

import asyncio
import inspect
import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


def new_id() -> str:
    """Hyphenated UUID v4: resource IDs."""
    return str(uuid.uuid4())


def new_job_id() -> str:
    """32-char hex: job IDs (real ones look like ff80808288d41e1b018990260955686a)."""
    return uuid.uuid4().hex


def new_request_id() -> str:
    return uuid.uuid4().hex.upper()


def now_millis() -> str:
    """RFC 3339 with milliseconds, UTC."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class Job:
    status: str = "RUNNING"  # RUNNING | SUCCESS | FAIL | INIT | PENDING_PAYMENT
    entities: dict = field(default_factory=dict)
    job_id: str = ""
    job_type: str = ""
    begin_time: str = ""
    end_time: str | None = None
    error_code: str | None = None
    fail_reason: str | None = None
    effect: Callable | None = None  # internal: never serialized
    chaos_fail: object = None  # internal: chaos rule that forces this job to FAIL

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "entities": self.entities,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "begin_time": self.begin_time,
            "end_time": self.end_time,
            "error_code": self.error_code,
            "fail_reason": self.fail_reason,
        }


class JobEngine:
    """Shared async job engine: submit effects that mutate state after a delay."""

    def __init__(self, delay_range: tuple[float, float] = (1.0, 3.0)):
        self.jobs: dict[str, Job] = {}
        self.delay_range = delay_range

    async def submit(
        self,
        job_type: str,
        entities: dict,
        effect: Callable[[], Coroutine[Any, Any, tuple[str, str] | None]],
    ) -> str:
        """Submit a job. The effect returns None on success or (error_code, fail_reason)."""
        job_id = new_job_id()
        # Chaos hook (ROADMAP 1.2): a job-mode rule marked during this request
        # forces the submitted job to FAIL instead of running its effect.
        chaos_fail = None
        if getattr(self, "chaos", None):
            chaos_fail = self.chaos.consume_job_failure()
        self.jobs[job_id] = Job(
            status="RUNNING",
            entities=entities,
            job_id=job_id,
            job_type=job_type,
            begin_time=now_millis(),
            effect=effect,
            chaos_fail=chaos_fail,
        )
        asyncio.create_task(self._run(job_id))
        return job_id

    async def _run(self, job_id: str):
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)
        job = self.jobs.get(job_id)
        if job is None or job.status != "RUNNING":
            return  # already force-completed via complete_now()
        if job.chaos_fail is not None:
            self._apply_result(job, (job.chaos_fail.error_code, job.chaos_fail.error_msg))
            return
        result = job.effect()
        if inspect.iscoroutine(result):
            result = await result
        self._apply_result(job, result)

    def _apply_result(self, job: Job, result):
        job.end_time = now_millis()
        if result is None:
            job.status = "SUCCESS"
        else:
            job.status = "FAIL"
            job.error_code, job.fail_reason = result

    def complete_now(self, job_id: str) -> bool:
        """Force-complete a RUNNING job synchronously: test hook.

        TestClient (and other in-process clients) never run the background
        asyncio task, so jobs stay RUNNING forever. This runs the effect
        immediately and marks the job SUCCESS. Only call from sync context.
        """
        job = self.jobs.get(job_id)
        if job is None or job.status != "RUNNING":
            return False
        if job.chaos_fail is not None:
            self._apply_result(job, (job.chaos_fail.error_code, job.chaos_fail.error_msg))
            return True
        result = job.effect()
        if inspect.iscoroutine(result):
            result = asyncio.run(result)
        self._apply_result(job, result)
        return True

    def complete_all(self) -> int:
        """Force-complete every RUNNING job: test hook (sync context only)."""
        n = 0
        for job_id in list(self.jobs):
            if self.jobs[job_id].status == "RUNNING":
                if self.complete_now(job_id):
                    n += 1
        return n

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def patch(self, job_id: str, fn: Callable[[Job], None]):
        job = self.jobs.get(job_id)
        if job:
            fn(job)


def mark_sub_jobs_success(job: Job):
    """Flip entities.sub_jobs[*] to SUCCESS: the real ShowJob behavior."""
    subs = job.entities.get("sub_jobs", [])
    for sj in subs:
        sj["status"] = "SUCCESS"
        sj["end_time"] = now_millis()
