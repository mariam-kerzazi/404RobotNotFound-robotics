"""Long-running tasks (like test runs) that the web page can watch live.

The page starts a job, gets back an id, and then asks "any new lines since
line N?" about twice a second until the job is done.
"""
import threading
import traceback
import uuid
from collections import OrderedDict
from typing import Callable

MAX_JOBS = 20  # forget old jobs so memory doesn't grow forever


class Job:
    def __init__(self, title: str):
        self.id = uuid.uuid4().hex[:8]
        self.title = title
        self.lines = []
        self.done = False
        self.exit_code = None
        self._lock = threading.Lock()

    def add_line(self, line: str) -> None:
        with self._lock:
            self.lines.append(line)

    def snapshot(self, since: int) -> dict:
        with self._lock:
            return {
                "id": self.id,
                "title": self.title,
                "lines": self.lines[since:],
                "next": len(self.lines),
                "done": self.done,
                "exit_code": self.exit_code,
            }


_jobs: "OrderedDict[str, Job]" = OrderedDict()
_jobs_lock = threading.Lock()


def start(title: str, work: Callable[[Callable[[str], None]], int]) -> Job:
    """Run work(add_line) in the background. work must return an exit code (0 = success)."""
    job = Job(title)

    def runner():
        try:
            job.exit_code = work(job.add_line)
        except Exception as e:  # show the error in the page instead of crashing
            job.add_line(f"ERROR: {e}")
            job.add_line(traceback.format_exc(limit=2))
            job.exit_code = -1
        finally:
            job.done = True

    with _jobs_lock:
        _jobs[job.id] = job
        while len(_jobs) > MAX_JOBS:
            _jobs.popitem(last=False)
    threading.Thread(target=runner, name=f"job-{job.id}", daemon=True).start()
    return job


def get(job_id: str):
    with _jobs_lock:
        return _jobs.get(job_id)
