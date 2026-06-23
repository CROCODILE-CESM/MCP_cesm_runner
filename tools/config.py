"""Tools for querying and changing CESM case XML configuration."""

import subprocess
from pathlib import Path


def _case_check(case_dir: str) -> Path | str:
    case = Path(case_dir).expanduser()
    if not (case / "CaseStatus").exists():
        return f"ERROR: {case_dir} does not look like a CESM case"
    return case


def xmlquery(case_dir: str, variable: str) -> str:
    """
    Query a CESM XML configuration variable.

    Runs ./xmlquery <variable> from the case directory and returns the value.
    Variable names are case-sensitive (e.g., STOP_N, RUN_STARTDATE, NTASKS_OCN).
    Pass variable='--listall' to list every defined variable.
    """
    case = _case_check(case_dir)
    if isinstance(case, str):
        return case

    result = subprocess.run(
        ["./xmlquery", variable],
        cwd=case,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return output.strip() or f"No output from xmlquery {variable}"


def xmlchange(case_dir: str, variable: str, value: str) -> str:
    """
    Change a CESM XML configuration variable.

    Runs ./xmlchange <variable>=<value> from the case directory.
    Example: variable='STOP_N', value='5' sets the run length to 5 time units.
    Use xmlquery first to confirm the current value before changing.
    """
    case = _case_check(case_dir)
    if isinstance(case, str):
        return case

    result = subprocess.run(
        ["./xmlchange", f"{variable}={value}"],
        cwd=case,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return f"FAILED (returncode={result.returncode}):\n{output.strip()}"
    return output.strip() or f"Set {variable}={value} successfully"


def preview_run(case_dir: str) -> str:
    """
    Preview what a CESM run will look like without actually submitting.

    Runs ./preview_run which shows the PE layout, estimated memory, wallclock,
    and the batch submission script that would be used. Useful for validating
    resource settings before committing to case_submit.
    """
    case = _case_check(case_dir)
    if isinstance(case, str):
        return case

    result = subprocess.run(
        ["./preview_run"],
        cwd=case,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return output.strip() or "preview_run produced no output"
