"""Tools for the CESM case lifecycle: setup, build, submit."""

import subprocess
from pathlib import Path


def _run_case_script(case_dir: str, script: str, extra_args: list[str] | None = None, timeout: int = 7200) -> str:
    case = Path(case_dir).expanduser()
    if not (case / "CaseStatus").exists():
        return f"ERROR: {case_dir} does not look like a CESM case"

    cmd = [f"./{script}"] + (extra_args or [])
    result = subprocess.run(
        cmd,
        cwd=case,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr.strip() else "")
    if result.returncode != 0:
        output = f"FAILED (returncode={result.returncode}):\n" + output
    return output.strip()


def case_setup(case_dir: str, clean: bool = False) -> str:
    """
    Run ./case.setup for a CESM case.

    Generates namelists, batch scripts, and the env_mach_specific.xml file.
    Pass clean=True to run './case.setup --clean' (removes prior setup artifacts).
    Must be run before case_build.
    """
    args = ["--clean"] if clean else []
    return _run_case_script(case_dir, "case.setup", args)


def case_build(case_dir: str, sharedlib_only: bool = False, model_only: bool = False) -> str:
    """
    Compile a CESM case (./case.build).

    Builds shared libraries and the model executable.
    Pass sharedlib_only=True or model_only=True to build in stages.
    This can take 10–30 minutes; the tool will wait and return the full output.
    """
    args = []
    if sharedlib_only:
        args.append("--sharedlib-only")
    if model_only:
        args.append("--model-only")
    return _run_case_script(case_dir, "case.build", args, timeout=3600)


def case_submit(case_dir: str, no_batch: bool = False, resubmit: bool = False) -> str:
    """
    Submit a CESM case to the batch system (./case.submit).

    Pass no_batch=True to run interactively instead of via PBS/slurm.
    Pass resubmit=True to resubmit a case that was previously run.
    Returns the submission confirmation and job ID.
    """
    args = []
    if no_batch:
        args.append("--no-batch")
    if resubmit:
        args.append("--resubmit")
    return _run_case_script(case_dir, "case.submit", args)
