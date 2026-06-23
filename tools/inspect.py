"""Tools for inspecting CESM cases — listing, status, input data."""

import os
import subprocess
from pathlib import Path


def list_cases(search_root: str, max_depth: int = 4) -> str:
    """
    Walk a directory tree and return all CESM case directories found.

    A directory is identified as a CESM case if it contains a CaseStatus file.
    Returns a newline-separated list of absolute paths.
    """
    root = Path(search_root).expanduser()
    if not root.exists():
        return f"ERROR: {search_root} does not exist"

    cases = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > max_depth:
            dirnames.clear()
            continue
        if "CaseStatus" in filenames:
            cases.append(dirpath)
            dirnames.clear()  # don't recurse into case dirs

    if not cases:
        return f"No CESM cases found under {search_root}"
    return "\n".join(sorted(cases))


def get_case_status(case_dir: str) -> str:
    """
    Return the full build/run/submit status of a CESM case.

    Reads the CaseStatus log and env_build.xml to report what steps are complete.
    """
    case = Path(case_dir).expanduser()
    status_file = case / "CaseStatus"
    if not status_file.exists():
        return f"ERROR: No CaseStatus found in {case_dir} — is this a CESM case?"

    status_text = status_file.read_text()

    # Also try xmlquery for a quick summary of key variables
    summary_vars = ["CASE", "COMPSET", "GRID", "MACH", "RUN_STARTDATE", "STOP_OPTION", "STOP_N"]
    xml_lines = []
    for var in summary_vars:
        result = subprocess.run(
            ["./xmlquery", var],
            cwd=case,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            xml_lines.append(result.stdout.strip())

    output = "=== CaseStatus ===\n" + status_text
    if xml_lines:
        output += "\n\n=== Key config ===\n" + "\n".join(xml_lines)
    return output


def check_input_data(case_dir: str) -> str:
    """
    Verify that all required input data files are staged for this CESM case.

    Runs ./check_input_data from the case directory and returns the output.
    This will report any missing files that need to be downloaded before the run.
    """
    case = Path(case_dir).expanduser()
    if not (case / "CaseStatus").exists():
        return f"ERROR: {case_dir} does not look like a CESM case"

    result = subprocess.run(
        ["./check_input_data"],
        cwd=case,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr
    return output if output.strip() else "check_input_data produced no output (returncode={})".format(result.returncode)
