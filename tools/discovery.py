"""Discovery tools — list compsets and machines available in a CESM install."""

import subprocess
from pathlib import Path


def list_compsets(cesmroot: str, filter: str = "") -> str:
    """
    List available compsets in a CESM installation.

    cesmroot: path to the CESM installation (e.g. ~/work/installs/cesm3_maddd_new)
    filter: optional substring to filter compset names (e.g. 'MOM6', 'NYF', 'JRA')

    Uses the CIME query_config script. Returns long-name compsets and their aliases.
    """
    cesm = Path(cesmroot).expanduser()
    query_script = cesm / "cime" / "scripts" / "query_config"
    if not query_script.exists():
        # Try alternate location
        query_script = cesm / "bin" / "query_config"
    if not query_script.exists():
        return f"ERROR: query_config not found in {cesmroot}/cime/scripts/ or {cesmroot}/bin/"

    result = subprocess.run(
        [str(query_script), "--compsets", "all"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    if filter:
        lines = [l for l in output.splitlines() if filter.lower() in l.lower()]
        if not lines:
            return f"No compsets matching '{filter}' found in {cesmroot}"
        return "\n".join(lines)
    return output.strip()
