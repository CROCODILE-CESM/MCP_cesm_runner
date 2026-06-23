"""Resource handlers for cesm:// URIs."""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("cesm-runner-resources")


@mcp.resource("cesm://case/{case_dir}/env")
def case_env(case_dir: str) -> str:
    """All XML configuration variables for a CESM case, merged from env_*.xml files."""
    case = Path(case_dir).expanduser()
    env_files = sorted(case.glob("env_*.xml"))
    if not env_files:
        return f"No env_*.xml files found in {case_dir}"

    result = subprocess.run(
        ["./xmlquery", "--listall"],
        cwd=case,
        capture_output=True,
        text=True,
    )
    return result.stdout or "Could not retrieve env variables"


@mcp.resource("cesm://case/{case_dir}/status")
def case_status_resource(case_dir: str) -> str:
    """Full CaseStatus log for a CESM case."""
    f = Path(case_dir).expanduser() / "CaseStatus"
    if not f.exists():
        return f"No CaseStatus in {case_dir}"
    return f.read_text()


@mcp.resource("cesm://case/{case_dir}/logs")
def case_logs(case_dir: str) -> str:
    """List of log files in a CESM case directory and its run/ subdirectory."""
    case = Path(case_dir).expanduser()
    logs = []
    for d in [case, case / "run"]:
        if d.exists():
            for p in sorted(d.glob("*.log*")):
                stat = p.stat()
                logs.append(f"{p}  ({stat.st_size} bytes, mtime={stat.st_mtime:.0f})")
    return "\n".join(logs) if logs else f"No log files found in {case_dir}"
