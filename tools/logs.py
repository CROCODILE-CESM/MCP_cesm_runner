"""Tools for monitoring CESM run logs and job queue status."""

import subprocess
import re
from pathlib import Path


def tail_log(case_dir: str, component: str = "cesm", lines: int = 100) -> str:
    """
    Return the most recent lines from a CESM run log.

    Searches the case directory and its run/ subdirectory for log files.
    component: one of 'cesm', 'ocn', 'atm', 'ice', 'rof', or 'all' to show all logs found.
    Returns the last <lines> lines of the most recently modified matching log.
    """
    case = Path(case_dir).expanduser()
    if not case.exists():
        return f"ERROR: {case_dir} does not exist"

    search_dirs = [case, case / "run"]
    candidates = []
    for d in search_dirs:
        if not d.exists():
            continue
        if component == "all":
            candidates.extend(d.glob("*.log*"))
            candidates.extend(d.glob("*/*.log*"))
        else:
            candidates.extend(d.glob(f"{component}.log*"))
            candidates.extend(d.glob(f"*{component}*.log*"))

    if not candidates:
        return f"No {component} log files found in {case_dir} or {case_dir}/run/"

    # Most recently modified log
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    log_file = candidates[0]

    result = subprocess.run(
        ["tail", f"-{lines}", str(log_file)],
        capture_output=True,
        text=True,
    )
    header = f"=== {log_file.name} (last {lines} lines) ===\n"
    return header + (result.stdout or "(empty)")


def get_job_status(case_dir: str) -> str:
    """
    Check the PBS/slurm batch queue status for the most recent job submitted from this case.

    Reads the CaseStatus log to extract the job ID, then queries the scheduler.
    Returns job state (R=running, Q=queued, C=complete, F=failed) and resource usage.
    """
    case = Path(case_dir).expanduser()
    status_file = case / "CaseStatus"
    if not status_file.exists():
        return f"ERROR: {case_dir} does not look like a CESM case"

    status_text = status_file.read_text()

    # Extract job ID from CaseStatus — typically looks like "job id is 12345.derecho..."
    job_id_match = re.search(r"job id(?:\s+is)?\s+(\S+)", status_text, re.IGNORECASE)
    if not job_id_match:
        # Also try "Submitted batch job NNNN"
        job_id_match = re.search(r"[Ss]ubmitted.*?(\d{5,})", status_text)
    if not job_id_match:
        return "Could not find a job ID in CaseStatus. Has case_submit been run?\n\nCaseStatus tail:\n" + "\n".join(status_text.splitlines()[-20:])

    job_id = job_id_match.group(1)

    # Try qstat (PBS/Derecho)
    result = subprocess.run(
        ["qstat", "-xf", job_id],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return f"Job {job_id}:\n{result.stdout}"

    # Fallback: squeue (slurm)
    result = subprocess.run(
        ["squeue", "--job", job_id, "--format=%i %j %T %M %l %R"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return f"Job {job_id}:\n{result.stdout}"

    return f"Job ID {job_id} found in CaseStatus but not in PBS or slurm queue (may have completed or failed)."
