"""Tools for the CESM case lifecycle: setup, build, submit."""

import subprocess
from pathlib import Path

from .container import container_exec


def _run_case_script(
    case_dir: str,
    script: str,
    extra_args: list[str] | None = None,
    timeout: int = 7200,
    container: str = "",
) -> str:
    case = Path(case_dir).expanduser()
    if not (case / "CaseStatus").exists():
        return f"ERROR: {case_dir} does not look like a CESM case"

    cmd_str = f"./{script}" + (" " + " ".join(extra_args) if extra_args else "")

    if container:
        return container_exec(container, str(case), cmd_str)

    result = subprocess.run(
        [f"./{script}"] + (extra_args or []),
        cwd=case,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr.strip() else "")
    if result.returncode != 0:
        output = f"FAILED (returncode={result.returncode}):\n" + output
    return output.strip()


def case_setup(case_dir: str, clean: bool = False, container: str = "") -> str:
    """
    Run ./case.setup for a CESM case.

    Generates namelists, batch scripts, and env_mach_specific.xml.
    Pass clean=True to run './case.setup --clean'.
    Pass container=<session_name> to run inside a crocontainer session (see start_container).
    Must be run before case_build.
    """
    args = ["--clean"] if clean else []
    return _run_case_script(case_dir, "case.setup", args, container=container)


def case_build(
    case_dir: str,
    sharedlib_only: bool = False,
    model_only: bool = False,
    container: str = "",
) -> str:
    """
    Compile a CESM case (./case.build).

    Pass container=<session_name> to compile inside a crocontainer session — this is
    the recommended path for fast iteration since it avoids queue wait times and uses
    the pre-installed compilers and MPI in the container.

    On Derecho without a container this can take 10–30 minutes in a batch job.
    Inside crocontainer it runs interactively and returns immediately on completion.
    """
    args = []
    if sharedlib_only:
        args.append("--sharedlib-only")
    if model_only:
        args.append("--model-only")
    return _run_case_script(case_dir, "case.build", args, timeout=3600, container=container)


def case_submit(
    case_dir: str,
    no_batch: bool = False,
    resubmit: bool = False,
    container: str = "",
) -> str:
    """
    Submit a CESM case (./case.submit).

    Pass container=<session_name> to run inside a crocontainer session.
    When using a container, also pass no_batch=True — the container runs interactively
    and does not have access to PBS/slurm, so batch submission will fail.

    container + no_batch=True is the fast-iteration path: model runs synchronously
    inside the container and returns output to this session with no queue wait.
    """
    args = []
    if no_batch:
        args.append("--no-batch")
    if resubmit:
        args.append("--resubmit")
    return _run_case_script(case_dir, "case.submit", args, container=container)
